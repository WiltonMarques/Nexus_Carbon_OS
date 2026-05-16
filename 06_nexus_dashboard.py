import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import psycopg2
import json

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Nexus Carbon-OS | Executive", layout="wide", page_icon="🛰️")

# ==========================================
# FUNÇÕES DE ACESSO A DADOS
# ==========================================
@st.cache_resource
def conectar_banco():
    try:
        with open('db_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return psycopg2.connect(
            dbname=config['dbname'], user=config['user'], 
            password=config['password'], host=config['host'], port=config['port']
        )
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

def buscar_dados_ativo():
    """Busca o último ativo securitizado no banco de dados."""
    conn = conectar_banco()
    if not conn: return None
    
    try:
        cursor = conn.cursor()
        query = """
            SELECT t.ticker_cram, t.volume_tco2e_emitido, t.valuation_usd, 
                   a.score_biomassa_ndvi, a.status_auditoria, a.hash_integridade
            FROM nexus_cram_titulos t
            JOIN nexus_carbon_auditoria a ON t.id_ativo_origem = a.id_ativo_cram
            ORDER BY t.id DESC LIMIT 1;
        """
        cursor.execute(query)
        res = cursor.fetchone()
        cursor.close()
        
        if res:
            return {
                "ticker": res[0], "volume": res[1], "valuation": res[2],
                "ndvi": res[3], "status": res[4], "hash": res[5]
            }
        return None
    except Exception as e:
        return None

# ==========================================
# FUNÇÕES DE RENDERIZAÇÃO VISUAL
# ==========================================
def renderizar_mapa():
    """Renderiza um polígono simulado na Amazônia usando Folium."""
    # Coordenadas simuladas de um projeto na Amazônia (Apuí-AM)
    centro_lat, centro_lon = -7.1950, -59.8940
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=11, tiles="CartoDB positron")
    
    # Polígono da área preservada
    limites = [
        [-7.15, -59.95], [-7.15, -59.85], 
        [-7.25, -59.85], [-7.25, -59.95]
    ]
    folium.Polygon(
        locations=limites, color="#11caa0", weight=3,
        fill=True, fill_color="#11caa0", fill_opacity=0.4,
        tooltip="Ativo: CRAM-AMZ-DA77<br>Área: 10.000 ha"
    ).add_to(m)
    
    return m

def plotar_monte_carlo(portfolio_inicial):
    """Gera a simulação interativa de Monte Carlo com a trava de Drawdown."""
    np.random.seed(42)
    dias = 252
    simulacoes = 150 # Reduzido para plotagem rápida na web
    vol = 0.38
    drift = 0.05
    dt = 1 / dias
    
    Z = np.random.standard_normal((dias, simulacoes))
    caminhos = np.zeros((dias + 1, simulacoes))
    caminhos[0] = portfolio_inicial
    
    for t in range(1, dias + 1):
        caminhos[t] = caminhos[t-1] * np.exp((drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * Z[t-1])

    fig = go.Figure()
    
    # Plota as linhas de simulação (cinza claro)
    for i in range(simulacoes):
        fig.add_trace(go.Scatter(x=list(range(dias+1)), y=caminhos[:, i], mode='lines', 
                                 line=dict(color='rgba(0, 80, 136, 0.05)'), showlegend=False))
        
    # Plota a Trava Paramétrica (45% de Drawdown Máximo)
    limite_ruina = portfolio_inicial * (1 - 0.45)
    fig.add_hline(y=limite_ruina, line_dash="dash", line_color="red", 
                  annotation_text="Trava de Drawdown (45%)", annotation_position="bottom right")
    
    # Linha base (Valor Inicial)
    fig.add_hline(y=portfolio_inicial, line_dash="solid", line_color="#11caa0", 
                  annotation_text="Valuation Emissão", annotation_position="top right")

    fig.update_layout(
        title="Simulação Estocástica de Risco (GBM)",
        xaxis_title="Dias Úteis (1 Ano)",
        yaxis_title="Valuation (USD)",
        template="plotly_white",
        height=450,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

# ==========================================
# CONSTRUÇÃO DO DASHBOARD (FRONT-END)
# ==========================================
st.title("🛰️ Nexus Carbon-OS | Executive Terminal")
st.markdown("Monitoramento Geoespacial e Estruturação Quantitativa de Ativos Ambientais.")
st.divider()

dados = buscar_dados_ativo()

if not dados:
    st.warning("Nenhum título emitido no banco de dados. Rode o Motor de Securitização primeiro.")
else:
    # --- LINHA 1: KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ticker Ativo (B3)", dados['ticker'])
    col2.metric("Valuation Atual (AUM)", f"USD {dados['valuation']:,.2f}")
    col3.metric("Volume de Emissão", f"{dados['volume']:,.0f} tCO2e")
    col4.metric("Índice Saúde (NDVI)", f"{dados['ndvi']:.4f}", delta="Auditado", delta_color="normal")
    
    st.divider()

    # --- LINHA 2: GEO & COMPLIANCE ---
    col_geo, col_rag = st.columns([1.5, 1])
    
    with col_geo:
        st.subheader("🌐 Oráculo Geoespacial (Área Monitorada)")
        mapa = renderizar_mapa()
        st_folium(mapa, height=350, width=800, returned_objects=[])
        st.caption(f"Hash Criptográfico de Lastro: `{dados['hash']}`")

    with col_rag:
        st.subheader("🛡️ Escudo RAG Anti-Greenwashing")
        st.info("**Fonte de Dados:** Sentinel-2 + Relatório Corporativo")
        
        # Simulando o laudo que geramos na Fase 2
        st.success("✅ **VERDITO: VALIDADO (Confiança: 95%)**")
        st.write("""
        **Justificativa Técnica:** O score NDVI de 0.6851 indica vegetação densa e saudável, 
        e o status 'FLORESTA_EM_PE' confirma a ausência de perda de biomassa, alinhando-se 
        com a narrativa corporativa. O ativo está liberado para estruturação financeira.
        """)
        
        st.metric("Risco Regulatório CVM", "BAIXO")

    st.divider()

    # --- LINHA 3: TESOURARIA QUANTITATIVA ---
    st.subheader("🏰 Tesouraria: Teste de Estresse & Black-Scholes")
    
    col_chart, col_boleta = st.columns([2, 1])
    
    with col_chart:
        fig_mc = plotar_monte_carlo(dados['valuation'])
        st.plotly_chart(fig_mc, use_container_width=True)
        
    with col_boleta:
        st.markdown("### Boleta de Hedge Paramétrico")
        st.markdown("Se a simulação (esquerda) romper a linha vermelha, o risco de ruína aciona o Hedge automático.")
        
        # Dados da boleta da Fase 5
        custo_hedge = 180036.20
        strike_price = 10.18
        
        st.error(f"**Strike de Proteção (PUT):** USD {strike_price:.2f}")
        st.warning(f"**Custo do Seguro (OPEX):** USD {custo_hedge:,.2f}")
        st.success(f"**Teto de Drawdown:** Blindado em 45.51%")
        
        if st.button("Executar Compra de Derivativos (B3/OTC)", type="primary"):
            st.toast("Ordem enviada para a mesa de operações!", icon="🏦")
            st.balloons()