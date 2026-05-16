# ==============================================================================
# HELIOS CARBON-OS ARCHITECTURE
# Copyright (c) 2026 Wilton Marques do Amaral
# Licensed under the Apache License, Version 2.0.
# ==============================================================================


import numpy as np
import psycopg2
import json
import logging

# ==========================================
# CONFIGURAÇÃO DE LOGS E SEMENTE
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
np.random.seed(42) # Reprodutibilidade na simulação

# ==========================================
# NEXUS CARBON-OS: MOTOR DE MONTE CARLO
# Fase 4: Gestão Estocástica de Tesouraria
# ==========================================

class MonteCarloRiskEngine:
    def __init__(self, config_file='db_config.json'):
        self.config_file = config_file
        self.config = self._carregar_configuracoes()
        
        # Parâmetros Estocásticos do Mercado de Carbono
        self.dias_uteis = 252 # 1 ano de pregão
        self.simulacoes = 10000 # Cenários de Monte Carlo
        self.volatilidade_anual = 0.38 # Alta volatilidade (38% a.a.) do carbono
        self.drift_anual = 0.05 # Expectativa de valorização de 5% a.a.
        
        # O Limite de Drawdown (DD) aceitável na estratégia
        self.teto_drawdown_max = 0.45 # Limite de 45%

    def _carregar_configuracoes(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def conectar_banco(self):
        return psycopg2.connect(
            dbname=self.config['dbname'], user=self.config['user'], 
            password=self.config['password'], host=self.config['host'], port=self.config['port']
        )

    def buscar_carteira_cram(self):
        """Busca o valor da tesouraria em CRAMs emitidos no banco de dados."""
        conn = self.conectar_banco()
        cursor = conn.cursor()
        
        # Soma todo o Valuation dos ativos emitidos
        cursor.execute("SELECT SUM(valuation_usd) FROM nexus_cram_titulos;")
        resultado = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return resultado if resultado else 0.0

    def simular_movimento_browniano(self, portfolio_inicial):
        """Aplica a matemática do Movimento Browniano Geométrico (GBM) para 10.000 cenários."""
        logging.info(f"⏳ Processando matrizes estocásticas: {self.simulacoes} cenários para {self.dias_uteis} dias...")
        
        dt = 1 / self.dias_uteis
        
        # Geração de choques aleatórios (Matriz 252 x 10.000)
        Z = np.random.standard_normal((self.dias_uteis, self.simulacoes))
        
        # Fórmula do GBM: dS = S * (mu * dt + sigma * dW)
        caminhos_precos = np.zeros((self.dias_uteis + 1, self.simulacoes))
        caminhos_precos[0] = portfolio_inicial
        
        for t in range(1, self.dias_uteis + 1):
            caminhos_precos[t] = caminhos_precos[t-1] * np.exp(
                (self.drift_anual - 0.5 * self.volatilidade_anual**2) * dt + 
                self.volatilidade_anual * np.sqrt(dt) * Z[t-1]
            )
            
        return caminhos_precos

    def auditar_limites_risco(self, portfolio_inicial, precos_finais):
        """Calcula o Value at Risk (VaR) e afere o teto de Drawdown."""
        # Ordena os 10.000 resultados do pior para o melhor
        resultados_ordenados = np.sort(precos_finais)
        
        # VaR a 95% de Confiança (Percentil 5)
        var_95_valor = np.percentile(resultados_ordenados, 5)
        perda_maxima_esperada = portfolio_inicial - var_95_valor
        
        # Cálculo de Drawdown Projetado no Pior Cenário
        drawdown_projetado = perda_maxima_esperada / portfolio_inicial
        
        print("\n" + "=" * 60)
        print("🏰 RELATÓRIO DE RISCO ESTOCÁSTICO (MONTE CARLO)")
        print("=" * 60)
        print(f"Patrimônio Atual (AUM):     USD {portfolio_inicial:,.2f}")
        print(f"Cenários Simulados:         {self.simulacoes:,}")
        print(f"Volatilidade Projetada:     {self.volatilidade_anual*100:.1f}% a.a.")
        print("-" * 60)
        print(f"VaR (95% Confiança):        USD -{perda_maxima_esperada:,.2f}")
        print(f"Valor Mínimo Projetado:     USD {var_95_valor:,.2f}")
        print("-" * 60)
        print(f"Drawdown Projetado (Pior Cenário): {drawdown_projetado*100:.2f}%")
        print(f"Limite Máximo Parametrizado:       {self.teto_drawdown_max*100:.2f}%")
        
        # Decisão Algorítmica de Proteção
        print("-" * 60)
        if drawdown_projetado > self.teto_drawdown_max:
            print("🚨 ALERTA VERMELHO DE TESOURARIA 🚨")
            print("O risco de mercado excede o teto paramétrico.")
            print("AÇÃO RECOMENDADA: COMPRAR OPÇÕES DE VENDA (PUT) NA ICE OU B3 IMEDIATAMENTE.")
        else:
            print("✅ TESOURARIA BLINDADA")
            print("A operação suporta a volatilidade dentro dos limites estritos de segurança.")
        print("=" * 60 + "\n")

    def executar_protecao(self):
        logging.info("⚙️ Iniciando varredura no Livro-Razão do Banco de Dados...")
        portfolio_atual = self.buscar_carteira_cram()
        
        if portfolio_atual <= 0:
            logging.error("❌ Não há fundos securitizados na tesouraria para proteger.")
            return
            
        logging.info(f"💵 Patrimônio Identificado: USD {portfolio_atual:,.2f}")
        
        # Executa a Matemática
        caminhos = self.simular_movimento_browniano(portfolio_atual)
        precos_finais = caminhos[-1] # Pegamos apenas o valor no dia 252
        
        # Audita os limites
        self.auditar_limites_risco(portfolio_atual, precos_finais)

if __name__ == "__main__":
    motor_risco = MonteCarloRiskEngine()
    motor_risco.executar_protecao()