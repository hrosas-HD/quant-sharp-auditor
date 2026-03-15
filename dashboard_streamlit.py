import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import google.generativeai as genai
import re
import json
import time
import random

# =====================================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Quant/Sharp Auditor Pro v7.9",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE LOGS PARA CONSOLA ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PERSONALIZADOS (LOOK PREMIUM + TABLAS) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stat-bar-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
        padding: 5px 0;
    }
    .stat-label { font-size: 0.8rem; color: #8b949e; text-align: center; flex: 1; font-weight: bold; text-transform: uppercase; }
    .stat-value { width: 40px; font-weight: bold; font-size: 1rem; }
    .bar-bg { flex: 3; height: 8px; background-color: #30363d; border-radius: 4px; margin: 0 10px; position: relative; overflow: hidden; }
    .bar-home { height: 100%; background-color: #e91e63; position: absolute; right: 50%; border-radius: 4px 0 0 4px; }
    .bar-away { height: 100%; background-color: #ffffff; position: absolute; left: 50%; border-radius: 0 4px 4px 0; }
    
    .bet-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .hit { border-left: 5px solid #238636; border-right: 1px solid #238636; }
    .miss { border-left: 5px solid #da3633; border-right: 1px solid #da3633; }
    
    /* Estilo de Tabla de Comparativa */
    .comp-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9rem; }
    .comp-table th { background-color: #161b22; color: #8b949e; padding: 10px; text-align: left; border-bottom: 2px solid #30363d; }
    .comp-table td { padding: 10px; border-bottom: 1px solid #21262d; }
    .status-badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .status-ok { background-color: #238636; color: white; }
    .status-no { background-color: #da3633; color: white; }
    
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    .loading-text { font-size: 1.1rem; color: #58a6ff; font-weight: bold; animation: pulse 1.5s infinite; text-align: center; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"

# =====================================================================
# COMPONENTES VISUALES
# =====================================================================
def render_stat_bar(label, val_home, val_away):
    total = float(val_home) + float(val_away) if (float(val_home) + float(val_away)) > 0 else 1.0
    p_home = (float(val_home) / total) * 50
    p_away = (float(val_away) / total) * 50
    st.markdown(f"""
        <div class="stat-bar-container">
            <div class="stat-value" style="text-align: right;">{val_home}</div>
            <div class="bar-bg"><div class="bar-home" style="width: {p_home}%;"></div><div class="bar-away" style="width: {p_away}%;"></div></div>
            <div class="stat-value" style="text-align: left;">{val_away}</div>
        </div>
        <div style="text-align: center; margin-top: -12px; margin-bottom: 15px;"><span class="stat-label">{label}</span></div>
    """, unsafe_allow_html=True)

# =====================================================================
# BARRA LATERAL
# =====================================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    manual_key = st.text_input("🔑 Gemini API Key:", type="password")
    model_option = st.selectbox("Motor:", ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-flash-latest"])
    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")
    if GEMINI_API_KEY: genai.configure(api_key=GEMINI_API_KEY)
    if st.button("🗑️ Limpiar Consola"):
        st.session_state.debug_logs = []
        st.rerun()
    st.divider()
    st.caption("Quant/Sharp v7.9 | Auditoría Métricas Simulación")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# MOTOR DE IA MEJORADO (EXTRACCIÓN DE MÉTRICAS)
# =====================================================================
def call_gemini_with_retry(model_name, parts, max_retries=5):
    try:
        model = genai.GenerativeModel(model_name=model_name, generation_config={"response_mime_type": "application/json"})
        for i in range(max_retries):
            try:
                add_log(f"Analizando con {model_name}...", "info")
                response = model.generate_content(parts)
                return response.text, None
            except Exception as e:
                if "429" in str(e):
                    time.sleep((i + 1) * 12); continue
                return None, str(e)
        return None, "Error de cuota."
    except Exception as e: return None, str(e)

def auditar_partido(pdf, img, model_choice):
    prompt = """
    [ROL] Auditor de Modelos Matemáticos Deportivos.
    
    [TAREA 1: VALIDACIÓN]
    Verifica si la IMAGEN contiene estadísticas de fútbol. Si no, devuelve "partido": "ERROR_IMAGEN_INVALIDA".

    [TAREA 2: EXTRACCIÓN EXHAUSTIVA DEL INFORME (PDF)]
    - Busca la "FASE 2: SIMULACIÓN".
    - Extrae: Goles totales proyectados, Corners totales proyectados, Tarjetas proyectadas, y si el modelo predijo "Ambos Marcan: SI/NO".
    - Extrae las 3 APUESTAS principales del resumen.

    [TAREA 3: CRUCE CON LA IMAGEN (REALIDAD)]
    - Calcula los valores reales de la imagen: Goles totales, Corners totales, Tarjetas totales, ¿Ambos marcaron?.
    - Extrae xG, Posesión, Disparos para visualización.

    [ESTRUCTURA JSON REQUERIDA]
    {
      "partido": "Local vs Visitante",
      "pronostico": "Resumen táctico corto",
      "marcador_final": "X-X",
      "estado": "🟢/🔴",
      "apuestas_detalle": [
          {"apuesta": "Texto apuesta 1", "hit": true}
      ],
      "comparativa_simulacion": [
          {"metrica": "Goles Totales", "informe": "Rango PDF", "real": "Valor IMG", "acerto": true},
          {"metrica": "Corners Totales", "informe": "Rango PDF", "real": "Valor IMG", "acerto": false},
          {"metrica": "Tarjetas Totales", "informe": "Rango PDF", "real": "Valor IMG", "acerto": true},
          {"metrica": "Ambos Marcan", "informe": "SI/NO", "real": "SI/NO", "acerto": true}
      ],
      "metricas_visuales": {
          "xG": [0.0, 0.0], "posesion": [0, 0], "disparos": [0, 0], "corners": [0, 0], "tarjetas": [0, 0]
      },
      "analisis_tecnico": "Explicación breve de la desviación o acierto del modelo."
    }
    """
    partes = [prompt, {"mime_type": "application/pdf", "data": pdf.getvalue()}, {"mime_type": "image/png", "data": img.getvalue()}]
    return call_gemini_with_retry(model_choice, partes)

# =====================================================================
# INTERFAZ PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

t1, t2, t3 = st.tabs(["📄 AUDITORÍA", "🛡️ APUESTA MAESTRA", "📊 PANEL DE CONTROL"])

with t1:
    st.info("Sube el Informe (PDF) y la captura de Estadísticas (Flashscore). Se realizará un cruce métrico total.")
    c1, c2 = st.columns(2)
    with c1: pdfs = st.file_uploader("PDFs", type="pdf", accept_multiple_files=True)
    with c2: imgs = st.file_uploader("Imágenes", type=["jpg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR CRUCE DE DATOS"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            with st.status("🚀 Procesando auditoría profunda...", expanded=True):
                for i in range(len(pdfs)):
                    res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option)
                    if not err:
                        try:
                            data = json.loads(res_raw)
                            if data.get('partido') != "ERROR_IMAGEN_INVALIDA":
                                row = {
                                    "partido": data['partido'], "pronostico": data['pronostico'],
                                    "marcador_final": data['marcador_final'], "estado": data['estado'],
                                    "tipo": "Individual", "analisis_tecnico": json.dumps(data)
                                }
                                supabase.table("auditoria_apuestas").insert(row).execute()
                                st.success(f"✅ Auditado: {data['partido']}")
                        except Exception as e: st.error(f"Error JSON: {e}")
                    else: st.error(err)
                    time.sleep(5)

with t3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            k1, k2, k3 = st.columns(3)
            hits = len(df[df['estado'].str.contains('🟢')])
            k1.metric("Análisis Totales", len(df))
            k2.metric("Acierto Estrategia", f"{(hits/len(df)*100):.1f}%")
            k3.metric("Filtro de Riesgo", "🛡️ Activo")
            
            st.divider()

            for index, row in df.iterrows():
                try:
                    full_data = json.loads(row['analisis_tecnico'])
                    with st.expander(f"{row['estado']} {row['partido']} | Final: {row['marcador_final']} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                        
                        # 1. SECCIÓN APUESTAS ELEGIDAS
                        st.markdown("#### 🎫 Evaluación de Apuestas Sugeridas")
                        b_cols = st.columns(3)
                        for i, bet in enumerate(full_data.get('apuestas_detalle', [])):
                            with b_cols[i % 3]:
                                status_cls = "hit" if bet["hit"] else "miss"
                                icon = "✅" if bet["hit"] else "❌"
                                st.markdown(f'<div class="bet-card {status_cls}"><strong>{icon} Apuesta {i+1}</strong><br><small>{bet["apuesta"]}</small></div>', unsafe_allow_html=True)

                        st.markdown("---")
                        
                        # 2. SECCIÓN TABLA COMPARATIVA DE MÉTRICAS (FASE 2)
                        st.markdown("#### 📉 Simulación (Fase 2) vs Realidad (Estadística)")
                        table_html = """<table class="comp-table"><thead><tr><th>Métrica</th><th>Informe (Predicción)</th><th>Imagen (Realidad)</th><th>Estado</th></tr></thead><tbody>"""
                        for m in full_data.get('comparativa_simulacion', []):
                            badge = "status-ok" if m['acerto'] else "status-no"
                            text_status = "ACIERTO" if m['acerto'] else "DESVIACIÓN"
                            table_html += f"<tr><td>{m['metrica']}</td><td>{m['informe']}</td><td>{m['real']}</td><td><span class='status-badge {badge}'>{text_status}</span></td></tr>"
                        table_html += "</tbody></table>"
                        st.markdown(table_html, unsafe_allow_html=True)

                        # 3. BARRAS ESTILO FLASHSCORE
                        st.markdown("#### 📊 Desempeño Visual del Encuentro")
                        mv = full_data.get('metricas_visuales', {})
                        render_stat_bar("Metas Esperadas (xG)", mv.get('xG',[0,0])[0], mv.get('xG',[0,0])[1])
                        render_stat_bar("Posesión de Balón %", mv.get('posesion',[0,0])[0], mv.get('posesion',[0,0])[1])
                        render_stat_bar("Patadas de Esquina", mv.get('corners',[0,0])[0], mv.get('corners',[0,0])[1])
                        
                        st.info(f"**Conclusión del Backtesting:** {full_data.get('analisis_tecnico', 'Sin datos.')}")
                except: st.write(row['analisis_tecnico'])
        else: st.info("Sin registros.")
    except Exception as e: st.error(f"Error DB: {e}")

st.sidebar.caption("Quant/Sharp v7.9 | Auditoría Profunda v2")
