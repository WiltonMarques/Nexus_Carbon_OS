# ==============================================================================
# HELIOS CARBON-OS ARCHITECTURE
# Copyright (c) 2026 Wilton Marques do Amaral
# Licensed under the Apache License, Version 2.0.
# ==============================================================================



import psycopg2
import json
import logging
import datetime
import hashlib
import uuid

# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==========================================
# NEXUS CARBON-OS: CRAM ENGINE
# Fase 3: Securitização e Valuation Financeiro
# ==========================================

class CRAMSecuritizationEngine:
    def __init__(self, config_file='db_config.json'):
        self.config_file = config_file
        self.config = self._carregar_configuracoes()
        
        # Parâmetros Estocásticos e de Tesouraria
        self.area_hectares = 10000 
        self.baseline_tco2e_ha = 350 
        self.preco_tco2e_usd = 18.50 
        self.buffer_risco = 0.20 # 20% retido como seguro

    def _carregar_configuracoes(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"❌ Erro ao ler configuração: {e}")
            return {}

    def conectar_banco(self):
        return psycopg2.connect(
            dbname=self.config['dbname'], user=self.config['user'], 
            password=self.config['password'], host=self.config['host'], port=self.config['port']
        )

    def preparar_tabela_titulos(self, cursor):
        """Cria o livro-razão (Ledger) financeiro na base de dados."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nexus_cram_titulos (
                id SERIAL PRIMARY KEY,
                ticker_cram VARCHAR(50) UNIQUE,
                id_ativo_origem VARCHAR(100),
                data_emissao TIMESTAMP,
                volume_tco2e_emitido FLOAT,
                valuation_usd FLOAT,
                hash_lastro_ambiental VARCHAR(256)
            );
        """)

    def buscar_ativos_elegiveis(self):
        """Busca projetos com floresta em pé que ainda não foram securitizados."""
        conn = self.conectar_banco()
        if not conn: return []
        
        cursor = conn.cursor()
        
        # [PATCH APLICADO] - Garante que a tabela exista antes do SELECT
        self.preparar_tabela_titulos(cursor)
        conn.commit()
        
        # Busca ativos saudáveis que ainda NÃO estão na tabela de títulos
        query = """
            SELECT a.id_ativo_cram, a.score_biomassa_ndvi, a.hash_integridade 
            FROM nexus_carbon_auditoria a
            LEFT JOIN nexus_cram_titulos t ON a.id_ativo_cram = t.id_ativo_origem
            WHERE a.status_auditoria = 'FLORESTA_EM_PE' AND t.id_ativo_origem IS NULL;
        """
        cursor.execute(query)
        ativos = cursor.fetchall()
        cursor.close()
        conn.close()
        return ativos

    def calcular_valuation(self, ndvi_score):
        """Aplica a matemática financeira sobre a biomassa."""
        # A saúde da folhagem define a eficiência da captura de carbono
        estoque_bruto_tco2e = self.area_hectares * self.baseline_tco2e_ha * ndvi_score
        
        # Desconto do Buffer de Risco
        volume_securitizavel = estoque_bruto_tco2e * (1 - self.buffer_risco)
        
        # Valuation Total
        valuation_usd = volume_securitizavel * self.preco_tco2e_usd
        
        return volume_securitizavel, valuation_usd

    def mintar_cram(self, id_ativo, ndvi, hash_ambiental):
        """Transforma o cálculo em um título gravado no banco."""
        volume, valuation = self.calcular_valuation(ndvi)
        
        # Geração do Ticker B3 Simulada
        sufixo = str(uuid.uuid4())[:4].upper()
        ticker = f"CRAM-AMZ-{sufixo}"
        
        data_emissao = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        conn = self.conectar_banco()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO nexus_cram_titulos 
                (ticker_cram, id_ativo_origem, data_emissao, volume_tco2e_emitido, valuation_usd, hash_lastro_ambiental)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (ticker, id_ativo, data_emissao, volume, valuation, hash_ambiental))
            
            conn.commit()
            logging.info(f"💎 SUCESSO! Ativo securitizado. Ticker [ {ticker} ] gerado.")
            
            # Retorno estruturado
            return {
                "Ticker": ticker,
                "Origem": id_ativo,
                "Volume Emitido (tCO2e)": round(volume, 2),
                "Valuation de Emissão (USD)": round(valuation, 2),
                "Lastro Ambiental (Hash)": hash_ambiental[:15] + "..."
            }
        except Exception as e:
            logging.error(f"❌ Erro ao mintar o CRAM: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()

    def executar_esteira_securitizacao(self):
        logging.info("⚙️ Iniciando Motor de Securitização de Ativos Ambientais...")
        
        ativos_elegiveis = self.buscar_ativos_elegiveis()
        
        if not ativos_elegiveis:
            logging.warning("⚠️ Nenhum ativo elegível encontrado (ou todos já foram securitizados).")
            return
        
        logging.info(f"📊 Encontrados {len(ativos_elegiveis)} ativos auditados prontos para securitização.")
        
        for ativo in ativos_elegiveis:
            id_ativo, ndvi, hash_amb = ativo
            logging.info(f"💰 Precificando ativo: {id_ativo} (NDVI: {ndvi})")
            
            recibo_cram = self.mintar_cram(id_ativo, ndvi, hash_amb)
            
            if recibo_cram:
                print("\n" + "=" * 60)
                print(f"🏦 TERMO DE EMISSÃO DE CRAM (PL 182/2024)")
                print("=" * 60)
                print(json.dumps(recibo_cram, indent=4, ensure_ascii=False))
                print("=" * 60 + "\n")

if __name__ == "__main__":
    motor_financeiro = CRAMSecuritizationEngine()
    motor_financeiro.executar_esteira_securitizacao()