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
    page_title="Quant/Sharp Auditor Pro v7.7",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE LOGS ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PERSONALIZADOS (FLASHCORE STYLE) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stat-bar-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 15px;
        padding: 5px 0;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #8b949e;
        text-align: center;
        flex: 1;
        font-weight: bold;
        text-transform: uppercase;
    }
    .stat-value {
        width: 40px;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .bar-bg {
        flex: 3;
        height: 12px;
        background-color: #30363d;
        border-radius: 6px;
        margin: 0 15px;
        position: relative;
        overflow: hidden;
    }
    .bar-home {
        height: 100%;
        background-color: #e91e63; /* Rosa/Rojo Flashscore */
        position: absolute;
        right: 50%;
        border-radius: 6px 0 0 6px;
    }
    .bar-away {
        height: 100%;
        background-color: #ffffff; /* Blanco Flashscore */
        position: absolute;
        left: 50%;
        border-radius: 0 6px 6px 0;
    }
    .bet-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 8px;
    }
    .hit { border-left: 5px solid #238636; }
    .miss { border-left: 5px solid #da3633; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"

# =====================================================================
# COMPONENTES VISUALES DE COMPARACIÓN
# =====================================================================
def render_stat_bar(label, val_home, val_away):
    """Genera una barra comparativa estilo Flashscore"""
    # Lógica para calcular porcentajes visuales (basado en el total de ambos)
    total = val_home + val_away if (val_home + val_away) > 0 else 1
    p_home = (val_home / total) * 50
    p_away = (val_away / total) * 50
    
    st.markdown(f"""
        <div class="stat-bar-container">
            <div class="stat-value" style="text-align: right;">{val_home}</div>
            <div class="bar-bg">
                <div class="bar-home" style="width: {p_home}%;"></div>
                <div class="bar-away" style="width: {p_away}%;"></div>
            </div>
            <div class="stat-value" style="text-align: left;">{val_away}</div>
        </div>
        <div style="text-align: center; margin-top: -15px; margin-bottom: 20px;">
            <span class="stat-label">{label}</span>
        </div>
    """, unsafe_allow_html=True)

# =====================================================================
# BARRA LATERAL (CONFIGURACIÓN)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Auditor Pro v7.7")
    manual_key = st.text_input("🔑 Gemini API Key (Manual):", type="password")
    model_option = st.selectbox("Motor:", ["gemini-1.5-flash", "gemini-2.0-flash"])
    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")
    
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    
    if st.button("🗑️ Limpiar Historial UI"):
        st.session_state.debug_logs = []
        st.rerun()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# MOTOR DE IA MEJORADO
# =====================================================================
def call_gemini_with_retry(model_name, parts, max_retries=5):
    try:
        model = genai.GenerativeModel(model_name=model_name, generation_config={"response_mime_type": "application/json"})
        for i in range(max_retries):
            try:
                response = model.generate_content(parts)
                return response.text, None
            except Exception as e:
                if "429" in str(e):
                    time.sleep((i + 1) * 10)
                    continue
                return None, str(e)
        return None, "Límite excedido."
    except Exception as e: return None, str(e)

def auditar_partido(pdf, img, model_choice):
    prompt = """
    [ROL] Auditor Senior de Datos Deportivos (Especialista en Backtesting).
    
    [TAREA 1: IDENTIFICACIÓN]
    Analiza la imagen. Si no son estadísticas de fútbol, devuelve "partido": "ERROR".
    
    [TAREA 2: EXTRACCIÓN DEL INFORME (PDF)]
    - Busca las 3 APUESTAS PRINCIPALES recomendadas.
    - Busca la FASE 2: SIMULACIÓN (Goles proyectados, corners proyectados).
    
    [TAREA 3: AUDITORÍA VS REALIDAD (IMAGEN)]
    - Compara cada una de las 3 apuestas: ¿Se cumplieron según la imagen?
    - Extrae datos reales para la comparativa visual: xG, Posesión, Disparos, Corners, Tarjetas.
    
    [ESTRUCTURA JSON REQUERIDA]
    {
      "partido": "Local vs Visitante",
      "pronostico": "Resumen de la estrategia",
      "marcador_final": "X-X",
      "estado": "🟢/🔴",
      "tipo": "Individual",
      "apuestas_detalle": [
          {"apuesta": "Nombre apuesta 1", "hit": true},
          {"apuesta": "Nombre apuesta 2", "hit": false},
          {"apuesta": "Nombre apuesta 3", "hit": true}
      ],
      "metricas_visuales": {
          "xG": [1.14, 1.61],
          "posesion": [68, 32],
          "disparos": [11, 5],
          "corners": [3, 3],
          "tarjetas": [4, 2]
      },
      "analisis_tecnico": "Un resumen corto de por qué se acertó o falló."
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
    col_u1, col_u2 = st.columns(2)
    with col_u1: pdfs = st.file_uploader("PDFs del Informe", type="pdf", accept_multiple_files=True)
    with col_u2: imgs = st.file_uploader("Capturas Flashscore", type=["jpg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR AUDITORÍA"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            with st.status("🚀 Analizando partidos...", expanded=True):
                for i in range(len(pdfs)):
                    st.write(f"Procesando: {pdfs[i].name}")
                    res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option)
                    if not err:
                        try:
                            data = json.loads(res_raw)
                            if data.get('partido') != "ERROR":
                                # Guardamos el JSON completo en la columna analisis_tecnico para procesarlo luego
                                data_to_save = data.copy()
                                # Para mantener compatibilidad con la tabla vieja, guardamos el JSON como texto
                                row = {
                                    "partido": data['partido'],
                                    "pronostico": data['pronostico'],
                                    "marcador_final": data['marcador_final'],
                                    "estado": data['estado'],
                                    "tipo": "Individual",
                                    "analisis_tecnico": json.dumps(data) # Guardamos todo el objeto aquí
                                }
                                supabase.table("auditoria_apuestas").insert(row).execute()
                                st.success(f"✅ Auditado: {data['partido']}")
                        except Exception as e: st.error(f"Error JSON: {e}")
                    else: st.error(err)
                    time.sleep(2)

with t3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            # --- MÉTRICAS ---
            k1, k2, k3 = st.columns(3)
            total = len(df)
            hits = len(df[df['estado'].str.contains('🟢')])
            k1.metric("Partidos", total)
            k2.metric("Acierto %", f"{(hits/total*100):.1f}%")
            k3.metric("Estatus", "🛡️ Protegido" if hits > 0 else "⚖️ Estable")
            
            st.divider()

            for index, row in df.iterrows():
                try:
                    # Intentamos cargar el JSON estructurado del análisis técnico
                    full_data = json.loads(row['analisis_tecnico'])
                    
                    with st.expander(f"{row['estado']} {row['partido']} | {row['marcador_final']}"):
                        # 1. SECCIÓN APUESTAS DEL INFORME
                        st.markdown("#### 🎫 Estatus de Apuestas del Informe")
                        bet_cols = st.columns(3)
                        for i, bet_item in enumerate(full_data.get('apuestas_detalle', [])):
                            with bet_cols[i % 3]:
                                status_icon = "✅" if bet_item['hit'] else "❌"
                                card_class = "hit" if bet_item['hit'] else "miss"
                                st.markdown(f"""
                                    <div class="bet-card {card_class}">
                                        <strong>{status_icon} Apuesta {i+1}</strong><br>
                                        <small>{bet_item['apuesta']}</small>
                                    </div>
                                """, unsafe_allow_html=True)

                        st.markdown("---")
                        
                        # 2. SECCIÓN COMPARATIVA VISUAL (ESTILO FLASHSCORE)
                        st.markdown("#### 📊 Estadísticas Finales (Realidad)")
                        m = full_data.get('metricas_visuales', {})
                        if m:
                            render_stat_bar("Metas Esperadas (xG)", m['xG'][0], m['xG'][1])
                            render_stat_bar("Posesión de Balón %", m['posesion'][0], m['posesion'][1])
                            render_stat_bar("Disparos Totales", m['disparos'][0], m['disparos'][1])
                            render_stat_bar("Patadas de Esquina", m['corners'][0], m['corners'][1])
                            render_stat_bar("Tarjetas Amarillas", m['tarjetas'][0], m['tarjetas'][1])
                        
                        # 3. ANÁLISIS TÉCNICO
                        st.info(f"**Conclusión del Auditor:** {full_data.get('analisis_tecnico', 'N/A')}")

                except:
                    # Fallback si el registro es de la versión vieja
                    with st.expander(f"{row['estado']} {row['partido']} (Versión Antigua)"):
                        st.write(row['analisis_tecnico'])
        else:
            st.info("Sin datos.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

st.sidebar.caption("Quant/Sharp v7.7 | Dashboard Flashscore Style")
