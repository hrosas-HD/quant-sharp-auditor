import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import re
import json
import time
import random

# =====================================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Quant/Sharp Auditor Pro v6.8",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (LOOK PREMIUM) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-family: 'Courier New', Courier, monospace; color: #58a6ff; }
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px 20px;
        border-radius: 12px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #238636;
        color: white;
        font-weight: bold;
        border: none;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .loading-text {
        font-size: 1.1rem;
        color: #58a6ff;
        font-weight: bold;
        animation: pulse 1.5s infinite;
        text-align: center;
        margin: 10px 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
# Credenciales de Supabase (Proyecto: tnxhmhoczcbfmhieaxgt)
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"

# Configuración de Gemini API
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    # Usamos tu clave de respaldo
    GEMINI_API_KEY = "AIzaSyCpeJM5HYnJuzH8YH1OG5lZ4D7BE4bTcTQ"

MODEL_NAME = "gemini-1.5-flash"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# LÓGICA DE IA CON CONTROL DE CUOTAS (ANTI-429)
# =====================================================================
def call_gemini_with_retry(model, parts, max_retries=3):
    """Maneja reintentos con espera para no saturar la API gratuita"""
    for i in range(max_retries):
        try:
            response = model.generate_content(parts)
            return response.text, None
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                wait = (i + 1) * 5 + random.random()
                time.sleep(wait)
                continue
            return None, err_msg
    return None, "Cuota agotada. Por favor espera 1 minuto."

def auditar_par_archivo(pdf, img):
    """Audita un solo par de archivos para mantener la estabilidad"""
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = """
        [ROL] Auditor Jefe de Datos Deportivos Pro.
        [TAREA] Compara la Fase 2 (Simulación) del PDF contra los resultados de la imagen.
        Devuelve un JSON con: partido, pronostico, marcador_final, goles_totales(int), corners(int), tarjetas(int), posesion, estado (🟢/🔴), sim_goles, sim_corners, exactitud_sim, analisis_tecnico, tipo: "Individual".
        """
        
        partes = [
            prompt, 
            {"mime_type": "application/pdf", "data": pdf.getvalue()},
            {"mime_type": "image/png", "data": img.getvalue()}
        ]
        
        return call_gemini_with_retry(model, partes)
    except Exception as e:
        return None, str(e)

# =====================================================================
# INTERFAZ DE USUARIO
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")
st.markdown("Protocolo Franco-Tirador v6.8 | Gestión de Riesgo y Backtesting")

tab1, tab2, tab3 = st.tabs(["📄 AUDITORÍA POR LOTES (P1)", "🛡️ APUESTA MAESTRA (P2)", "📊 PANEL DE CONTROL"])

# --- TAB 1: PROCESAMIENTO POR LOTES ---
with tab1:
    st.subheader("Fase 1: Control de Calidad de Informes")
    st.info("Sube tus informes PDF y las capturas de resultados. Se procesarán secuencialmente.")
    
    c1, c2 = st.columns(2)
    with c1:
        pdfs = st.file_uploader("Subir Informes PDF", type="pdf", accept_multiple_files=True, key="p1_pdf")
    with c2:
        imgs = st.file_uploader("Subir Imágenes de Resultados", type=["jpg", "png"], accept_multiple_files=True, key="p1_img")
    
    if st.button("▶ INICIAR PROCESAMIENTO SECUENCIAL"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            with st.status("🚀 Procesando archivos uno a uno...", expanded=True) as status:
                for i in range(len(pdfs)):
                    st.markdown(f'<p class="loading-text">Analizando Partido {i+1} de {len(pdfs)}...</p>', unsafe_allow_html=True)
                    
                    res_raw, err = auditar_par_archivo(pdfs[i], imgs[i])
                    
                    if err:
                        st.error(f"Error en {pdfs[i].name}: {err}")
                        continue
                    
                    try:
                        data = json.loads(res_raw)
                        supabase.table("auditoria_apuestas").insert(data).execute()
                        st.success(f"✅ Guardado: {data.get('partido')}")
                        time.sleep(2) # Pausa de seguridad para la API
                    except Exception as e:
                        st.error(f"Error al guardar datos: {e}")
                
                status.update(label="✅ Todos los partidos procesados", state="complete")
        else:
            st.warning("El número de PDFs y de Imágenes debe coincidir.")

# --- TAB 2: APUESTA MAESTRA (PROMPT 2) ---
with tab2:
    st.subheader("Fase 2: Validación de Apuesta Maestra")
    c_m1, c_m2 = st.columns([1, 1])
    with c_m1:
        m_text = st.text_area("Resultado del Prompt 2 (Texto)", height=250, placeholder="🛡️ LA APUESTA MAESTRA...")
    with c_m2:
        m_img = st.file_uploader("Captura de Estadísticas Reales", type=["jpg", "png"], key="p2_img")
    
    if st.button("▶ VALIDAR MAESTRA"):
        if m_text and m_img:
            with st.status("🔍 Verificando selección del Franco-Tirador...", expanded=True):
                model = genai.GenerativeModel(MODEL_NAME, generation_config={"response_mime_type": "application/json"})
                prompt = f"""
                [ROL] Auditor Franco-Tirador.
                [PRONÓSTICO]: {m_text}
                Verifica contra imagen real y devuelve JSON con tipo: "Maestra".
                """
                partes = [prompt, {"mime_type": "image/png", "data": m_img.getvalue()}]
                res_raw, err = call_gemini_with_retry(model, partes)
                
                if not err:
                    data = json.loads(res_raw)
                    supabase.table("auditoria_apuestas").insert(data).execute()
                    st.balloons()
                    st.success("✅ Apuesta Maestra registrada con éxito.")

# --- TAB 3: PANEL DE CONTROL ---
with tab3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            op = st.pills("Filtrar por:", ["Todos", "Individuales", "Apuestas Maestras"], default="Todos")
            
            df_v = df if op == "Todos" else df[df['tipo'] == ('Individual' if op == "Individuales" else 'Maestra')]
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Análisis", len(df_v))
            hits = len(df_v[df_v['estado'].str.contains('🟢')])
            win_rate = (hits/len(df_v)*100 if len(df_v)>0 else 0)
            k2.metric("Tasa de Acierto", f"{win_rate:.1f}%")
            k3.metric("Estado", "🛡️ Protegido" if win_rate > 65 else "⚖️ Estable")
            
            st.plotly_chart(px.pie(df_v, names='estado', hole=0.5, title="Distribución de Resultados"), use_container_width=True)
            st.subheader("Historial de Operaciones")
            st.dataframe(df_v[['fecha', 'partido', 'estado', 'tipo', 'analisis_tecnico']], use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros en la base de datos.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

st.sidebar.caption("Quant/Sharp v6.8 | Franco-Tirador Workflow")
