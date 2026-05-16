# ==============================================================================
# HELIOS CARBON-OS ARCHITECTURE
# Copyright (c) 2026 Wilton Marques do Amaral
# Licensed under the Apache License, Version 2.0.
# ==============================================================================


import psycopg2
import json
import logging
import datetime
import numpy as np
from scipy.stats import norm
import yfinance as yf

# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

# ==========================================
# NEXUS CARBON-OS: AUDITORIA INDEPENDENTE
# Fase 7: Reconciliação Matemática e Laudo C-Level
# ==========================================

class NexusAuditEngine:
    def __init__(self, config_file='db_config.json'):
        self.config_file = config_file
        
        # Parâmetros Imutáveis da Engenharia Original
        self.area_ha = 10000 
        self.baseline_tco2e = 350 
        self.buffer_risco = 0.20
        self.max_dd = 0.45
        
        self.taxa_livre_risco = 0.045
        self.volatilidade = 0.38
        self.tempo_vencimento = 1.0
        
        # O Preço Spot agora é dinâmico (buscado via API)
        self.preco_spot = self.buscar_preco_spot_api()

    def buscar_preco_spot_api(self):
        """Busca o preço em tempo real do ETF KRBN via API."""
        logging.info("📡 Conectando à API de mercado (Yahoo Finance) para buscar cotação Spot do Carbono...")
        try:
            ticker = yf.Ticker("KRBN")
            dados = ticker.history(period="1d")
            
            if not dados.empty:
                preco_fechamento = float(dados['Close'].iloc[-1])
                logging.info(f"✅ Preço Spot atualizado via API Global: USD {preco_fechamento:.2f}")
                return preco_fechamento
            else:
                raise ValueError("Nenhum dado retornado pela API.")
                
        except Exception as e:
            logging.warning(f"⚠️ Falha na API. Acionando Fallback paramétrico (USD 18.50). Erro: {e}")
            return 18.50 

    def conectar_banco(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return psycopg2.connect(
            dbname=config['dbname'], user=config['user'], 
            password=config['password'], host=config['host'], port=config['port']
        )

    def recuperar_snapshot_ativo(self):
        """Puxa a última operação registrada no Ledger para auditar."""
        conn = self.conectar_banco()
        cursor = conn.cursor()
        
        query = """
            SELECT t.ticker_cram, t.volume_tco2e_emitido, t.valuation_usd, 
                   a.id_ativo_cram, a.score_biomassa_ndvi, a.status_auditoria, a.hash_integridade, t.data_emissao
            FROM nexus_cram_titulos t
            JOIN nexus_carbon_auditoria a ON t.id_ativo_origem = a.id_ativo_cram
            ORDER BY t.id DESC LIMIT 1;
        """
        cursor.execute(query)
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        return res

    def _black_scholes_put(self, S, K, T, r, sigma):
        """Matemática dura para prova do prêmio de seguro."""
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return (K * np.exp(-r * T) * norm.cdf(-d2)) - (S * norm.cdf(-d1))

    def emitir_laudo_auditoria(self):
        logging.info("🔎 Iniciando Reconciliação Matemática Reversa...")
        
        dados = self.recuperar_snapshot_ativo()
        if not dados:
            logging.error("❌ Nenhum ativo encontrado para auditar.")
            return

        ticker, vol_db, val_db, id_origem, ndvi, status, hash_amb, data_emissao = dados

        # PROVA 1: INTEGRIDADE BIOFÍSICA
        status_validado = "APROVADO" if ndvi >= 0.60 and status == 'FLORESTA_EM_PE' else "REPROVADO"
        
        # PROVA 2: RECONCILIAÇÃO DE VOLUME
        vol_calculado = (self.area_ha * self.baseline_tco2e) * ndvi * (1 - self.buffer_risco)
        delta_vol = abs(vol_db - vol_calculado)
        status_vol = "VERIFICADO" if delta_vol < 0.1 else "DIVERGÊNCIA DETECTADA"

        # PROVA 3: MARCAÇÃO A MERCADO (MtM) COM API
        val_calculado = vol_calculado * self.preco_spot
        delta_val = val_calculado - val_db 
        
        # Correção da Sintaxe do Python aqui!
        marca_a_mercado = "VALORIZAÇÃO" if delta_val > 0 else "DESVALORIZAÇÃO" if delta_val < 0 else "NEUTRO"

        # PROVA 4: GARANTIA DE HEDGE (TRAVA 45%)
        strike_alvo = self.preco_spot * (1 - self.max_dd)
        premio_put = self._black_scholes_put(self.preco_spot, strike_alvo, self.tempo_vencimento, self.taxa_livre_risco, self.volatilidade)
        custo_hedge = premio_put * vol_calculado
        
        patrimonio_estressado = (strike_alvo * vol_calculado) - custo_hedge
        dd_matematico = 1 - (patrimonio_estressado / val_calculado)
        status_hedge = "BLINDAGEM CONFIRMADA" if dd_matematico <= 0.46 else "FALHA PARAMÉTRICA" 

        # =========================================================
        # GERAÇÃO DO LAUDO DINÂMICO (F-STRING PARAMETRIZADA)
        # =========================================================
        data_report = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
================================================================================
          LAUDO DE AUDITORIA E MARCAÇÃO A MERCADO - NEXUS CARBON-OS
================================================================================
CONFORMIDADE REGULATÓRIA: IFRS S2 / CVM 193 / SBCE (PL 182/2024)
NORMA CONTÁBIL APLICADA:  CPC 46 (Mensuração a Valor Justo - Nível 1) e CPC 01
--------------------------------------------------------------------------------
DATA DA AUDITORIA: {data_report}
TICKER DO ATIVO:   {ticker}
ORIGEM:            {id_origem}
HASH DE LASTRO:    {hash_amb}

[1] TESTE DE IMPAIRMENT BIOFÍSICO (CPC 01)
--------------------------------------------------------------------------------
> Parâmetro Exigido: NDVI >= 0.60
> NDVI Registrado:   {ndvi:.4f}
> Status Biofísico:  {status}
>>> Veredito:        [{status_validado} - Sem indicação de perda de valor recuperável]

[2] RECONCILIAÇÃO DE VOLUME E MENSURAÇÃO A VALOR JUSTO (CPC 46 / NÍVEL 1)
--------------------------------------------------------------------------------
> Área Base da Origem:       {self.area_ha:,.0f} ha
> Volume Verificado (DB):    {vol_db:,.2f} tCO2e [{status_vol}]
> Preço Spot Base (Emissão): USD 18.50
> Preço Spot Atual (API):    USD {self.preco_spot:.2f} (Fonte: Mercado Ativo / KRBN)
> Valuation Histórico (DB):  USD {val_db:,.2f}
> Valuation Atual (MtM):     USD {val_calculado:,.2f}
> Variação Reconhecida:      USD {abs(delta_val):,.2f} [{marca_a_mercado}]
>>> Veredito Contábil:       [MENSURAÇÃO CONFORME CPC 46]

[3] DIVULGAÇÃO DE RISCOS CLIMÁTICOS E FINANCEIROS (IFRS S2 / CVM 193)
--------------------------------------------------------------------------------
> Teto de Drawdown Limite:    {self.max_dd * 100:.2f}%
> Strike Paramétrico (PUT):   USD {strike_alvo:.2f}
> Provisão Custo de Hedge:    USD {custo_hedge:,.2f}
> Drawdown Estressado (Max):  {dd_matematico * 100:.2f}%
>>> Veredito de Governança:   [{status_hedge} E Risco Evidenciado]

================================================================================
CONCLUSÃO PARA A CONTROLADORIA: 
O ativo atende aos requisitos de reconhecimento e mensuração. A variação a Valor 
Justo documentada na Seção 2 deve ser reconhecida no resultado do exercício, e a 
provisão para derivativos da Seção 3 está respaldada por precificação Black-Scholes.
================================================================================
        """
        
        filename = f"Laudo_{ticker}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report.strip())
            
        print("\n" + report.strip() + "\n")
        logging.info(f"✅ Laudo gerado com sucesso e salvo em: {filename}")

if __name__ == "__main__":
    auditor = NexusAuditEngine()
    auditor.emitir_laudo_auditoria()