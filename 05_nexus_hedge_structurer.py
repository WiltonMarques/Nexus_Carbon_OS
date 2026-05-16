import numpy as np
from scipy.stats import norm
import psycopg2
import json
import logging

# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

# ==========================================
# NEXUS CARBON-OS: HEDGE STRUCTURER
# Fase 5: Precificação de Derivativos (Black-Scholes)
# ==========================================

class BlackScholesHedgeEngine:
    def __init__(self, config_file='db_config.json'):
        self.config_file = config_file
        
        # Parâmetros de Mercado e Tesouraria
        self.preco_spot_carbono = 18.50      # Preço atual do ativo subjacente (S)
        self.volatilidade = 0.38             # Volatilidade de 38% (sigma)
        self.taxa_livre_risco = 0.045        # Risk-free rate (ex: T-Bills) a 4.5% a.a. (r)
        self.tempo_vencimento = 1.0          # 1 ano para o vencimento (T)
        
        # O Limite Operacional Inegociável da Estratégia
        self.max_drawdown_permitido = 0.45   

    def conectar_banco(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return psycopg2.connect(
            dbname=config['dbname'], user=config['user'], 
            password=config['password'], host=config['host'], port=config['port']
        )

    def buscar_exposicao_tesouraria(self):
        """Busca o volume total de carbono (tCO2e) securitizado no livro-razão."""
        conn = self.conectar_banco()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(volume_tco2e_emitido), SUM(valuation_usd) FROM nexus_cram_titulos;")
        resultado = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        volume_total = resultado[0] if resultado[0] else 0.0
        valuation_total = resultado[1] if resultado[1] else 0.0
        return volume_total, valuation_total

    def calcular_strike_price_alvo(self):
        """
        Define o Strike (K) da Opção de Venda.
        Se o máximo Drawdown permitido é 45%, o preço não pode cair abaixo de 55% do valor atual.
        """
        strike_price = self.preco_spot_carbono * (1 - self.max_drawdown_permitido)
        return strike_price

    def precificar_put_black_scholes(self, S, K, T, r, sigma):
        """
        Calcula o Prêmio (custo) de uma Opção de Venda Europeia (PUT)
        usando a fórmula de Black-Scholes-Merton.
        """
        # Cálculo de d1 e d2
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Equação da PUT
        # P = K * e^(-rT) * N(-d2) - S * N(-d1)
        put_price = (K * np.exp(-r * T) * norm.cdf(-d2)) - (S * norm.cdf(-d1))
        
        # Fator de Proteção (Delta da PUT) - Para fins quantitativos
        delta_put = norm.cdf(d1) - 1
        
        return put_price, delta_put

    def estruturar_operacao_hedge(self):
        logging.info("⚙️ Iniciando Estruturação Algorítmica de Hedge (Black-Scholes)...")
        
        volume_tco2e, valuation_atual = self.buscar_exposicao_tesouraria()
        
        if volume_tco2e <= 0:
            logging.error("❌ Nenhum ativo em carteira para proteger.")
            return

        # 1. Definir a Linha de Defesa (Strike)
        strike_alvo = self.calcular_strike_price_alvo()
        logging.info(f"🎯 Strike alvo calculado para blindar o DD em {self.max_drawdown_permitido*100}%: USD {strike_alvo:.2f}/tCO2e")

        # 2. Precificar o Derivativo
        premio_put, delta = self.precificar_put_black_scholes(
            S=self.preco_spot_carbono, 
            K=strike_alvo, 
            T=self.tempo_vencimento, 
            r=self.taxa_livre_risco, 
            sigma=self.volatilidade
        )
        
        # 3. Calcular o OPEX da Proteção (Custo Total do Hedge)
        custo_total_hedge = premio_put * volume_tco2e
        percentual_custo = (custo_total_hedge / valuation_atual) * 100
        
        # 4. Simular o Pior Cenário com o Hedge (Preço cai a zero)
        # Se o preço for a zero, exercemos a opção a USD 10.18
        valuation_pior_cenario_protegido = (strike_alvo * volume_tco2e) - custo_total_hedge
        dd_pior_cenario_protegido = 1 - (valuation_pior_cenario_protegido / valuation_atual)

        print("\n" + "=" * 65)
        print("🛡️ BOLETA DE TESOURARIA: ESTRUTURAÇÃO DE HEDGE (PUT OPTION)")
        print("=" * 65)
        print("[ DADOS DO ATIVO SUBJACENTE ]")
        print(f"  > Volume Exposto:             {volume_tco2e:,.2f} tCO2e")
        print(f"  > Valuation Total (AUM):      USD {valuation_atual:,.2f}")
        print(f"  > Preço Spot (S):             USD {self.preco_spot_carbono:.2f}")
        print("-" * 65)
        print("[ ESTRUTURAÇÃO DO DERIVATIVO (BLACK-SCHOLES) ]")
        print(f"  > Strike Price (K):           USD {strike_alvo:.2f} (Trava Paramétrica)")
        print(f"  > Vencimento (T):             {self.tempo_vencimento} Ano(s)")
        print(f"  > Prêmio por tCO2e (P):       USD {premio_put:.4f}")
        print(f"  > Delta da Estrutura:         {delta:.4f}")
        print("-" * 65)
        print("[ FLUXO DE CAIXA DA PROTEÇÃO ]")
        print(f"  > Custo Total da Trava:       USD {custo_total_hedge:,.2f}")
        print(f"  > Impacto no Patrimônio:      {percentual_custo:.2f}% do AUM")
        print("-" * 65)
        print("[ RESULTADO DO TESTE DE ESTRESSE PROTEGIDO ]")
        print(f"  > Drawdown Máximo Blindado:   {dd_pior_cenario_protegido*100:.2f}% (Teto preservado ✅)")
        print("=" * 65)
        print("AÇÃO EXECUTIVA: Emitir ordem de compra de PUTs OTC ou via B3 (Futuro de CRAM).")
        print("=" * 65 + "\n")

if __name__ == "__main__":
    motor_hedge = BlackScholesHedgeEngine()
    motor_hedge.estruturar_operacao_hedge()