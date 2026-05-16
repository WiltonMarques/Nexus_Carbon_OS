import numpy as np
import datetime
import hashlib
import json
import logging
import psycopg2

# ==========================================
# CONFIGURAÇÃO DE LOGS PARA AUDITORIA
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==========================================
# NEXUS CARBON-OS: ORÁCULO GEOESPACIAL
# Fase 1: Ingestão Orbital e Time-Stamping
# ==========================================

class GeoSentinelEngine:
    def __init__(self, projeto_id, config_file='db_config.json'):
        self.projeto_id = projeto_id
        self.config_file = config_file
        logging.info(f"🛰️ Inicializando Oráculo Geoespacial para o projeto: {self.projeto_id}")

    def calcular_ndvi(self, banda_red: np.ndarray, banda_nir: np.ndarray) -> float:
        """Calcula o Índice de Vegetação (NDVI)."""
        logging.info("Processando matrizes de refletância (RED e NIR)...")
        np.seterr(divide='ignore', invalid='ignore')
        
        ndvi_matrix = (banda_nir.astype(float) - banda_red.astype(float)) / (banda_nir + banda_red)
        ndvi_medio = np.nanmean(ndvi_matrix)
        
        logging.info(f"Índice NDVI Médio calculado: {ndvi_medio:.4f}")
        return float(ndvi_medio)

    def gerar_lastro_criptografico(self, ndvi_score: float) -> dict:
        """Gera um Time-Stamp imutável via hash SHA-256."""
        data_captura = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        status = "FLORESTA_EM_PE" if ndvi_score >= 0.60 else "ALERTA_DEGRADACAO"
        
        payload_string = f"{self.projeto_id}|{data_captura}|{ndvi_score:.4f}|{status}"
        assinatura_sha256 = hashlib.sha256(payload_string.encode('utf-8')).hexdigest()

        dossie = {
            "id_ativo_cram": self.projeto_id,
            "timestamp_utc": data_captura,
            "score_biomassa_ndvi": round(ndvi_score, 4),
            "status_auditoria": status,
            "hash_integridade": assinatura_sha256
        }
        
        logging.info("🔒 Dossiê de lastro criptográfico gerado com sucesso.")
        return dossie

    def conectar_banco(self):
        """Lê o arquivo .json e estabelece conexão com o PostgreSQL usando as credenciais exatas."""
        logging.info(f"🔌 Lendo credenciais de segurança em '{self.config_file}'...")
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Conecta usando as credenciais exatas do JSON (nexus_carbon_os_db)
            logging.info(f"Conectando ao banco de dados: {config['dbname']} (Host: {config['host']})")
            conn = psycopg2.connect(
                dbname=config['dbname'], 
                user=config['user'], 
                password=config['password'], 
                host=config['host'], 
                port=config['port']
            )
            return conn
        except Exception as e:
            logging.error(f"❌ Falha ao carregar credenciais ou conectar ao BD: {e}")
            return None

    def persistir_banco_dados(self, dossie):
        """Cria a tabela e insere a prova de vida no banco relacional."""
        conn = self.conectar_banco()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            logging.info("🏗️ Verificando/Criando tabela 'nexus_carbon_auditoria'...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nexus_carbon_auditoria (
                    id SERIAL PRIMARY KEY,
                    id_ativo_cram VARCHAR(100),
                    timestamp_utc TIMESTAMP,
                    score_biomassa_ndvi FLOAT,
                    status_auditoria VARCHAR(50),
                    hash_integridade VARCHAR(256)
                );
            """)
            
            cursor.execute("""
                INSERT INTO nexus_carbon_auditoria 
                (id_ativo_cram, timestamp_utc, score_biomassa_ndvi, status_auditoria, hash_integridade)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                dossie['id_ativo_cram'], 
                dossie['timestamp_utc'], 
                dossie['score_biomassa_ndvi'], 
                dossie['status_auditoria'], 
                dossie['hash_integridade']
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            logging.info(f"💾 Sucesso! Ativo ambiental gravado permanentemente no banco. Hash: {dossie['hash_integridade'][:10]}...")
            return True
        except Exception as e:
            logging.error(f"❌ Erro ao gravar dados no banco: {e}")
            if conn:
                conn.rollback()
            return False

    def executar_varredura_simulada(self):
        """Simula ingestão satelital, calcula, gera hash e salva no BD."""
        matriz_red = np.random.uniform(400, 800, (100, 100))
        matriz_nir = np.random.uniform(2500, 4000, (100, 100))

        score_ndvi = self.calcular_ndvi(matriz_red, matriz_nir)
        dossie_final = self.gerar_lastro_criptografico(score_ndvi)
        
        self.persistir_banco_dados(dossie_final)
        
        return dossie_final

# ==========================================
# EXECUÇÃO DO MÓDULO
# ==========================================
if __name__ == "__main__":
    print("-" * 60)
    print("NEXUS CARBON-OS | THE SENTINEL PROTOCOL")
    print("-" * 60)
    
    motor_geo = GeoSentinelEngine(projeto_id="CRAM-AMZ-2026-001")
    resultado_auditoria = motor_geo.executar_varredura_simulada()
    
    print("\n[RESUMO DO ATIVO SECURITIZADO]")
    print(json.dumps(resultado_auditoria, indent=4, ensure_ascii=False))
    print("-" * 60)