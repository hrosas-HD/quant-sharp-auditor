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
    page_title="Quant/Sharp Auditor Pro v7.6",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN PARA LOGS ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.debug_logs.append(f"[{timestamp}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PERSONALIZADOS ---
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

# =====================================================================
# BARRA LATERAL (CONFIGURACIÓN DE SEGURIDAD)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Configuración Crítica")
    
    manual_key = st.text_input("🔑 Gemini API Key (Manual):", type="password")
    
    model_option = st.selectbox(
        "Motor de Inteligencia:",
        ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-flash-latest"],
        index=0
    )

    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")

    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            if st.button("🔍 Probar Validez de Clave"):
                models = [m.name for m in genai.list_models()]
                st.success("✅ Clave Activa")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    if st.button("🗑️ Limpiar Consola"):
        st.session_state.debug_logs = []
        st.rerun()

    st.divider()
    st.caption("v7.6 | Validación de Imagen Estricta")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# LÓGICA DE IA CON CONTROL DE ROBUSTEZ
# =====================================================================
def call_gemini_with_retry(model_name, parts, max_retries=5):
    if not GEMINI_API_KEY:
        return None, "No hay API Key configurada."
        
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"response_mime_type": "application/json"}
        )
        
        for i in range(max_retries):
            try:
                add_log(f"Iniciando intento {i+1} con {model_name}...", "info")
                response = model.generate_content(parts)
                return response.text, None
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    delay_match = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', err_str)
                    wait = int(delay_match.group(1)) + 2 if delay_match else (i + 1) * 15
                    time.sleep(wait)
                    continue
                return None, err_str
        return None, "Error persistente tras reintentos."
    except Exception as e:
        return None, f"Error de motor: {str(e)}"

def auditar_par_archivo(pdf, img, model_choice):
    # PROMPT MEJORADO CON VALIDACIÓN DE SEGURIDAD
    prompt = """
    [ROL] Auditor Senior de Datos Deportivos.
    
    [PASO 1: VALIDACIÓN DE ARCHIVOS]
    Analiza la IMAGEN proporcionada. ¿Contiene estadísticas reales de un partido de fútbol? 
    - SI NO contiene estadísticas deportivas (ej. es una foto personal, paisaje, meme, etc.), DEBES devolver el JSON con el campo "partido": "ERROR_IMAGEN_INVALIDA".
    
    [PASO 2: AUDITORÍA]
    Si la imagen es válida, extrae la Fase 2 (Simulación) del PDF y compárala con los resultados de la IMAGEN.
    
    [REGLA DE SALIDA]
    Devuelve un OBJETO JSON con esta estructura exacta:
    {
      "partido": "Nombre de equipos o ERROR_IMAGEN_INVALIDA",
      "pronostico": "Resumen",
      "marcador_final": "Resultado",
      "goles_totales": int,
      "corners": int,
      "tarjetas": int,
      "posesion": "XX%",
      "estado": "🟢/🔴",
      "sim_goles": "rango",
      "sim_corners": "rango",
      "exactitud_sim": "XX%",
      "analisis_tecnico": "Tabla comparativa Markdown",
      "tipo": "Individual"
    }
    """
    partes = [
        prompt, 
        {"mime_type": "application/pdf", "data": pdf.getvalue()},
        {"mime_type": "image/png", "data": img.getvalue()}
    ]
    return call_gemini_with_retry(model_choice, partes)

# =====================================================================
# INTERFAZ DE USUARIO PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

tab1, tab2, tab3 = st.tabs(["📄 AUDITORÍA INDIVIDUAL (P1)", "🛡️ APUESTA MAESTRA (P2)", "📊 PANEL DE CONTROL"])

with tab1:
    st.subheader("Fase 1: Control de Calidad de Simulaciones")
    c1, c2 = st.columns(2)
    with c1:
        pdfs = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    with c2:
        imgs = st.file_uploader("Subir Imágenes", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR PROCESAMIENTO"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            with st.status("🚀 Procesando archivos...", expanded=True) as status:
                for i in range(len(pdfs)):
                    st.markdown(f'<p class="loading-text">Analizando Partido {i+1}...</p>', unsafe_allow_html=True)
                    res_raw, err = auditar_par_archivo(pdfs[i], imgs[i], model_option)
                    
                    if err:
                        st.error(f"Fallo en {pdfs[i].name}: {err}")
                        continue
                    
                    try:
                        datos = json.loads(res_raw)
                        item = datos[0] if isinstance(datos, list) else datos
                        
                        # FILTRO DE VALIDACIÓN DE IMAGEN
                        if item.get('partido') == "ERROR_IMAGEN_INVALIDA":
                            st.error(f"❌ El archivo {imgs[i].name} no parece ser una captura de estadísticas. Saltando...")
                            add_log(f"Imagen inválida detectada en {imgs[i].name}", "warning")
                        else:
                            supabase.table("auditoria_apuestas").insert(item).execute()
                            st.success(f"✅ Guardado: {item.get('partido')}")
                            add_log(f"Éxito en {item.get('partido')}", "success")
                        
                        time.sleep(5)
                    except Exception as e:
                        st.error(f"Error interpretando datos: {e}")
                status.update(label="✅ Todos los procesos terminados", state="complete")

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
            with st.status("🔍 Verificando selección...", expanded=True):
                prompt = f"Analiza si la imagen es de estadísticas deportivas. Si no, devuelve partido: 'ERROR'. Si sí, audita el pronóstico: {m_text} y devuelve JSON con tipo: 'Maestra'."
                partes = [prompt, {"mime_type": "image/png", "data": m_img.getvalue()}]
                res_raw, err = call_gemini_with_retry(model_option, partes)
                
                if not err:
                    try:
                        data = json.loads(res_raw)
                        item = data[0] if isinstance(data, list) else data
                        if item.get('partido') == "ERROR":
                            st.error("La imagen no es válida para auditoría.")
                        else:
                            supabase.table("auditoria_apuestas").insert(item).execute()
                            st.balloons()
                            st.success("✅ Apuesta Maestra guardada.")
                    except:
                        st.error("Error en formato.")

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
            
            for index, row in df_v.iterrows():
                with st.expander(f"{row['estado']} {row['partido']} | {row['fecha'].strftime('%d/%m/%Y %H:%M')}"):
                    st.markdown(row['analisis_tecnico'])
        else:
            st.info("Sin registros.")
    except Exception as e:
        st.error(f"Error de base de datos.")

st.sidebar.caption("Quant/Sharp v7.6 | Validación Activa")
