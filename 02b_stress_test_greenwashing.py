import psycopg2
import json
import logging
import datetime
import hashlib
from google import genai

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class StressTestEngine:
    def __init__(self, config_file='db_config.json'):
        self.config_file = config_file
        self.config = self._carregar_configuracoes()
        self.client = genai.Client(api_key=self.config.get('gemini_api_key', ''))

    def _carregar_configuracoes(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def conectar_banco(self):
        return psycopg2.connect(
            dbname=self.config['dbname'], user=self.config['user'], 
            password=self.config['password'], host=self.config['host'], port=self.config['port']
        )

    def injetar_dado_falso(self, id_ativo):
        """Simula a captura de uma área degradada (NDVI baixo)."""
        logging.warning(f"⚠️ INJETANDO DADO DE ESTRESSE: Simulando desmatamento para o ativo {id_ativo}...")
        conn = self.conectar_banco()
        cursor = conn.cursor()
        
        data_captura = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ndvi_critico = 0.3201 # Muito abaixo de 0.60
        status = "ALERTA_DEGRADACAO"
        
        hash_integridade = hashlib.sha256(f"{id_ativo}|{data_captura}|{ndvi_critico}|{status}".encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO nexus_carbon_auditoria 
            (id_ativo_cram, timestamp_utc, score_biomassa_ndvi, status_auditoria, hash_integridade)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_ativo, data_captura, ndvi_critico, status, hash_integridade))
        
        conn.commit()
        cursor.close()
        conn.close()
        logging.info("💉 Injeção concluída. O banco de dados agora registra alerta crítico na área.")
        return data_captura, ndvi_critico, status

    def executar_auditoria_ia(self, id_ativo, narrativa_corporativa, dados_reais):
        logging.info("🛡️ ACIONANDO ESCUDO RAG: Auditando narrativa contra dados reais...")
        
        data_ref, ndvi, status_real = dados_reais
        
        prompt = f"""
        VOCÊ É UM AUDITOR SÊNIOR DE RISCO ESG E GREENWASHING DA CVM.
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
            "justificativa": "explicação técnica curta e letal"
        }}
        """

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        res_text = response.text.replace('```json', '').replace('```', '').strip()
        laudo = json.loads(res_text)
        
        print("\n" + "=" * 60)
        print(f"🚨 LAUDO DE STRESS TEST: {id_ativo}")
        print("=" * 60)
        print(json.dumps(laudo, indent=4, ensure_ascii=False))
        print("=" * 60)

if __name__ == "__main__":
    motor_stress = StressTestEngine()
    
    id_alvo = "CRAM-AMZ-2026-FRAUDE"
    
    # 1. Força a degradação no banco
    dados = motor_stress.injetar_dado_falso(id_alvo)
    
    # 2. A narrativa mentirosa da empresa (A Isca)
    narrativa_fraudulenta = """
    É com imenso orgulho que anunciamos os resultados do projeto CRAM-AMZ-2026-FRAUDE. 
    Neste último trimestre, nossas medições indicam que a floresta atingiu o seu ápice 
    de preservação histórica. As copas estão extremamente densas, a biodiversidade está 
    florescendo e não há qualquer sinal de intervenção humana ou perda de folhagem. 
    Nosso compromisso com a integridade do crédito de carbono é total e inabalável.
    """
    
    # 3. O Choque
    motor_stress.executar_auditoria_ia(id_alvo, narrativa_fraudulenta, dados)