import psycopg2
import json
import logging
from google import genai

# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==========================================
# NEXUS CARBON-OS: ESCUDO SEMÂNTICO (RAG)
# Fase 2: Auditoria Anti-Greenwashing (Atualizado Google GenAI SDK)
# ==========================================

class NexusRAGShield:
    def __init__(self, config_file='db_config.json'):
        self.config_file = config_file
        self.config = self._carregar_configuracoes()
        self.client = None
        
        if 'gemini_api_key' in self.config:
            # Nova sintaxe de inicialização do cliente
            self.client = genai.Client(api_key=self.config['gemini_api_key'])
            logging.info("🔑 Cliente Google GenAI inicializado com sucesso via config.json.")
        else:
            logging.error("❌ 'gemini_api_key' não encontrada no arquivo db_config.json.")

    def _carregar_configuracoes(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"❌ Erro ao ler arquivo de configuração: {e}")
            return {}

    def conectar_banco(self):
        try:
            return psycopg2.connect(
                dbname=self.config['dbname'], 
                user=self.config['user'], 
                password=self.config['password'], 
                host=self.config['host'], 
                port=self.config['port']
            )
        except Exception as e:
            logging.error(f"❌ Erro de conexão com o banco: {e}")
            return None

    def recuperar_dados_reais(self, id_ativo):
        conn = self.conectar_banco()
        if not conn: return None
        
        try:
            cursor = conn.cursor()
            query = "SELECT timestamp_utc, score_biomassa_ndvi, status_auditoria FROM nexus_carbon_auditoria WHERE id_ativo_cram = %s ORDER BY id DESC LIMIT 1;"
            cursor.execute(query, (id_ativo,))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            logging.error(f"❌ Erro ao recuperar dados do BD: {e}")
            return None

    def executar_auditoria_ia(self, id_ativo, narrativa_corporativa):
        if not self.client:
            logging.error("❌ Cliente de IA não configurado. Abortando auditoria.")
            return

        dados_reais = self.recuperar_dados_reais(id_ativo)
        
        if not dados_reais:
            logging.error("❌ Ativo não encontrado no banco de dados.")
            return
        
        data_ref, ndvi, status_real = dados_reais
        logging.info(f"🧠 Iniciando análise semântica para o ativo {id_ativo}...")

        prompt = f"""
        VOCÊ É UM AUDITOR SÊNIOR DE RISCO ESG E GREENWASHING.
        Sua tarefa é confrontar a NARRATIVA CORPORATIVA com os DADOS REAIS DO SATÉLITE.

        DADOS REAIS (SISTEMA SENTINEL):
        - ID do Ativo: {id_ativo}
        - Data da Captura: {data_ref}
        - Score NDVI (Saúde Vegetal): {ndvi}
        - Status Biofísico: {status_real}

        NARRATIVA CORPORATIVA PARA AUDITORIA:
        "{narrativa_corporativa}"

        CRITÉRIOS DE VERDITO:
        1. VALIDADO: Se a narrativa for condizente com os dados reais.
        2. ALERTA_GREENWASHING: Se a narrativa exagerar os resultados ou omitir degradação.

        RETORNE APENAS UM JSON (sem formatação markdown) COM A SEGUINTE ESTRUTURA:
        {{
            "verdito": "VALIDADO" ou "ALERTA_GREENWASHING",
            "confianca": 0-100,
            "justificativa": "explicação técnica curta"
        }}
        """

        try:
            # Nova chamada da API apontando para o modelo atualizado
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            res_text = response.text.replace('```json', '').replace('```', '').strip()
            laudo = json.loads(res_text)
            
            print("-" * 60)
            print(f"📄 LAUDO DE CONFORMIDADE: {id_ativo}")
            print("-" * 60)
            print(json.dumps(laudo, indent=4, ensure_ascii=False))
            print("-" * 60)
            
            return laudo
        except Exception as e:
            logging.error(f"❌ Falha no processamento da IA: {e}")
            return None

if __name__ == "__main__":
    shield = NexusRAGShield()
    
    # Exemplo de narrativa para teste (Ajustada para o seu banco)
    narrativa_exemplo = """
    Nosso projeto CRAM-AMZ-2026-001 mantém integridade absoluta. 
    As imagens de satélite confirmam que não houve qualquer perda de biomassa, 
    garantindo a segurança dos créditos emitidos e a saúde florestal.
    """
    
    shield.executar_auditoria_ia("CRAM-AMZ-2026-001", narrativa_exemplo)