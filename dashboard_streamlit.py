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
    page_title="Quant/Sharp Auditor Pro v7.0",
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
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"

# PRIORIDAD DE CLAVE: Secrets de Streamlit -> Nueva Clave proporcionada
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "AIzaSyC66lmTl5kVQbsT954jEBkMcCfJczLohGc")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("⚠️ Falta la configuración de GEMINI_API_KEY.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# LÓGICA DE IA CON CONTROL DE ROBUSTEZ
# =====================================================================
def call_gemini_with_retry(model_name, parts, max_retries=3):
    """Llamada a Gemini con reintentos para manejar errores 429 y 404"""
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"response_mime_type": "application/json"}
        )
        
        for i in range(max_retries):
            try:
                response = model.generate_content(parts)
                return response.text, None
            except Exception as e:
                err_str = str(e)
                # Error de Cuota (Límite de peticiones)
                if "429" in err_str:
                    time.sleep((i + 1) * 5 + random.random())
                    continue
                # Error de Modelo no encontrado
                if "404" in err_str:
                    return None, f"El modelo '{model_name}' no existe en esta región/cuenta. Cambia el motor en la barra lateral."
                return None, err_str
        return None, "Error de cuota tras reintentos."
    except Exception as e:
        return None, f"Error de motor: {str(e)}"

def auditar_par_archivo(pdf, img, model_choice):
    """Audita un par de archivos individualmente para mayor precisión"""
    prompt = """
    [ROL] Auditor Jefe de Datos Deportivos Pro.
    [TAREA] Compara la Fase 2 (Simulación) del PDF contra los resultados de la imagen real.
    [REGLA] Devuelve un JSON con: partido, pronostico, marcador_final, goles_totales(int), corners(int), tarjetas(int), posesion, estado (🟢/🔴), sim_goles, sim_corners, exactitud_sim, analisis_tecnico, tipo: "Individual".
    """
    partes = [
        prompt, 
        {"mime_type": "application/pdf", "data": pdf.getvalue()},
        {"mime_type": "image/png", "data": img.getvalue()}
    ]
    return call_gemini_with_retry(model_choice, partes)

# =====================================================================
# INTERFAZ DE USUARIO
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

with st.sidebar:
    st.header("⚙️ Configuración")
    model_option = st.selectbox(
        "Motor de Inteligencia:",
        ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-flash-latest"],
        index=0,
        help="Si un modelo falla, prueba otro de la lista."
    )
    
    if st.button("🔍 Probar Conexión API"):
        try:
            models = [m.name for m in genai.list_models()]
            st.success("Conexión Exitosa")
            st.write("Modelos disponibles en tu cuenta:", [m.split('/')[-1] for m in models])
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            
    st.divider()
    st.caption("v7.0 | New API Key Integration")

tab1, tab2, tab3 = st.tabs(["📄 AUDITORÍA INDIVIDUAL (P1)", "🛡️ APUESTA MAESTRA (P2)", "📊 PANEL DE CONTROL"])

# --- PESTAÑA 1: LOTES ---
with tab1:
    st.subheader("Fase 1: Control de Calidad de Simulaciones")
    st.info("Sube informes y capturas. El sistema los emparejará y analizará secuencialmente.")
    
    c1, c2 = st.columns(2)
    with c1:
        pdfs = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    with c2:
        imgs = st.file_uploader("Subir Imágenes", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR PROCESAMIENTO"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            with st.status("🚀 Auditando...", expanded=True) as status:
                for i in range(len(pdfs)):
                    msg = f"Analizando Partido {i+1}: {pdfs[i].name}"
                    st.markdown(f'<p class="loading-text">{msg}</p>', unsafe_allow_html=True)
                    
                    res_raw, err = auditar_par_archivo(pdfs[i], imgs[i], model_option)
                    
                    if err:
                        st.error(f"Fallo en {pdfs[i].name}: {err}")
                        continue
                    
                    try:
                        data = json.loads(res_raw)
                        supabase.table("auditoria_apuestas").insert(data).execute()
                        st.success(f"✅ Guardado: {data.get('partido')}")
                        time.sleep(2) # Pausa técnica para evitar bloqueos
                    except Exception as e:
                        st.error(f"Error interpretando datos: {e}")
                status.update(label="✅ Todos los procesos terminados", state="complete")
        else:
            st.warning("Debes subir la misma cantidad de archivos e imágenes.")

# --- PESTAÑA 2: APUESTA MAESTRA ---
with tab2:
    st.subheader("Fase 2: Validación de la Guillotina")
    cm1, cm2 = st.columns([1, 1])
    with cm1:
        m_text = st.text_area("Texto del Franco-Tirador (P2)", height=250)
    with cm2:
        m_img = st.file_uploader("Estadísticas del Partido Maestro", type=["jpg", "png", "jpeg"], key="master_img")
    
    if st.button("▶ VALIDAR APUESTA MAESTRA"):
        if m_text and m_img:
            with st.status("🔍 Verificando selección final...", expanded=True):
                prompt = f"[ROL] Auditor Franco-Tirador. [PRONÓSTICO]: {m_text}. Verifica contra la imagen real y devuelve JSON con tipo: 'Maestra'."
                partes = [prompt, {"mime_type": "image/png", "data": m_img.getvalue()}]
                res_raw, err = call_gemini_with_retry(model_option, partes)
                
                if not err:
                    try:
                        data = json.loads(res_raw)
                        supabase.table("auditoria_apuestas").insert(data).execute()
                        st.balloons()
                        st.success("✅ Apuesta Maestra auditada y guardada.")
                    except:
                        st.error("Error en formato de respuesta.")
                else:
                    st.error(err)

# --- PESTAÑA 3: DASHBOARD ---
with tab3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            filt = st.pills("Ver:", ["Todos", "Individuales", "Apuestas Maestras"], default="Todos")
            
            df_v = df if filt == "Todos" else df[df['tipo'] == ('Individual' if filt == "Individuales" else 'Maestra')]
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Partidos", len(df_v))
            hits = len(df_v[df_v['estado'].str.contains('🟢')])
            k2.metric("Acierto %", f"{(hits/len(df_v)*100 if len(df_v)>0 else 0):.1f}%")
            k3.metric("Estatus", "🛡️ Seguro" if hits > 0 else "⚖️ Estable")
            
            st.dataframe(df_v[['fecha', 'partido', 'estado', 'tipo', 'analisis_tecnico']], use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos en el historial.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

st.sidebar.caption("Quant/Sharp v7.0 | Workflow Blindado")
