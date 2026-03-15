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

# =====================================================================
# BARRA LATERAL (CONFIGURACIÓN DE SEGURIDAD)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Configuración Crítica")
    
    manual_key = st.text_input("🔑 Gemini API Key (Manual):", type="password", help="Pega aquí tu nueva clave si la anterior expiró.")
    
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
                add_log("Prueba de conexión exitosa.", "success")
        except Exception as e:
            st.error(f"❌ Error de Clave: {e}")
            add_log(f"Fallo en prueba de conexión: {str(e)}", "error")
    else:
        st.warning("⚠️ Sin clave configurada.")

    if st.button("🗑️ Limpiar Consola"):
        st.session_state.debug_logs = []
        st.rerun()

    st.divider()
    st.caption("v7.6 | Validación de Imagen Estricta")

# Inicialización de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# LÓGICA DE IA CON CONTROL DE ROBUSTEZ Y VALIDACIÓN
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
                add_log(f"Respuesta recibida de {model_name}.", "success")
                return response.text, None
            except Exception as e:
                err_str = str(e)
                add_log(f"Error en intento {i+1}: {err_str}", "warning")
                
                if "429" in err_str:
                    delay_match = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', err_str)
                    if delay_match:
                        wait = int(delay_match.group(1)) + 2
                    else:
                        wait = (i + 1) * 15 + random.random()
                    
                    add_log(f"Cuota agotada. Pausa de {wait:.2f}s...", "info")
                    time.sleep(wait)
                    continue
                
                if "400" in err_str and "expired" in err_str.lower():
                    return None, "La clave de API ha expirado."
                
                return None, err_str
                
        return None, "Error persistente tras reintentos."
    except Exception as e:
        add_log(f"Error crítico de motor: {str(e)}", "error")
        return None, f"Error de motor: {str(e)}"

def auditar_par_archivo(pdf, img, model_choice):
    # PROMPT MEJORADO CON GUARDIÁN DE VALIDACIÓN
    prompt = """
    [ROL] Auditor Senior de Datos Deportivos.
    
    [PASO 1: VALIDACIÓN DE ARCHIVOS]
    Analiza la IMAGEN proporcionada. ¿Contiene estadísticas reales de un partido de fútbol (marcador, corners, tarjetas, posesión)? 
    - SI NO contiene estadísticas deportivas claras (ej. es una foto, una captura de código, un dashboard de software, un meme, etc.), DEBES devolver el JSON con el campo "partido": "ERROR_IMAGEN_INVALIDA".
    
    [PASO 2: AUDITORÍA]
    Si la imagen es válida, extrae la Fase 2 (Simulación) del PDF proporcionado y compárala punto por punto con los resultados de la IMAGEN.
    
    [REGLA DE SALIDA]
    Devuelve un OBJETO JSON (o una lista con un objeto) con esta estructura exacta:
    {
      "partido": "Nombre de equipos o ERROR_IMAGEN_INVALIDA",
      "pronostico": "Resumen recomendaciones",
      "marcador_final": "Resultado real",
      "goles_totales": int,
      "corners": int,
      "tarjetas": int,
      "posesion": "XX%",
      "estado": "🟢 (Acierto) o 🔴 (Fallo)",
      "sim_goles": "rango proyectado",
      "sim_corners": "rango proyectado",
      "exactitud_sim": "XX%",
      "analisis_tecnico": "Tabla comparativa Markdown detallada",
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

# --- PESTAÑA 1: LOTES ---
with tab1:
    st.subheader("Fase 1: Control de Calidad de Simulaciones")
    st.info("Sube informes y capturas. El sistema validará la autenticidad de las imágenes antes de procesar.")
    
    c1, c2 = st.columns(2)
    with c1:
        pdfs = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    with c2:
        imgs = st.file_uploader("Subir Imágenes", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR PROCESAMIENTO"):
        if not GEMINI_API_KEY:
            st.error("Introduce una clave de API en la barra lateral.")
        elif pdfs and imgs and len(pdfs) == len(imgs):
            with st.status("🚀 Procesando archivos...", expanded=True) as status:
                for i in range(len(pdfs)):
                    msg_ui = f"Analizando Partido {i+1}: {pdfs[i].name}"
                    st.markdown(f'<p class="loading-text">{msg_ui}</p>', unsafe_allow_html=True)
                    
                    res_raw, err = auditar_par_archivo(pdfs[i], imgs[i], model_option)
                    
                    if err:
                        st.error(f"Fallo en {pdfs[i].name}: {err}")
                        add_log(f"Error procesando {pdfs[i].name}: {err}", "error")
                        continue
                    
                    try:
                        datos_procesados = json.loads(res_raw)
                        lista_datos = datos_procesados if isinstance(datos_procesados, list) else [datos_procesados]
                        
                        for item in lista_datos:
                            # FILTRO DE SEGURIDAD CONTRA IMÁGENES ERRÓNEAS
                            if item.get('partido') == "ERROR_IMAGEN_INVALIDA":
                                st.error(f"❌ El archivo {imgs[i].name} no parece ser una captura de estadísticas. Saltando...")
                                add_log(f"Imagen inválida detectada en {imgs[i].name}", "warning")
                            else:
                                supabase.table("auditoria_apuestas").insert(item).execute()
                                nombre_partido = item.get('partido', 'Desconocido')
                                st.success(f"✅ Guardado: {nombre_partido}")
                                add_log(f"Éxito en {nombre_partido}. Guardado en DB.", "success")
                        
                        time.sleep(5)
                    except Exception as e:
                        st.error(f"Error interpretando datos: {e}")
                        add_log(f"Error JSON en {pdfs[i].name}: {str(e)}", "error")
                status.update(label="✅ Todos los procesos terminados", state="complete")
        else:
            st.warning("Debes subir la misma cantidad de archivos e imágenes.")

    # --- CONSOLA DE ERRORES ---
    st.divider()
    with st.expander("🛠️ Consola de Depuración Técnica", expanded=len(st.session_state.debug_logs) > 0):
        if st.session_state.debug_logs:
            log_content = "\n".join(st.session_state.debug_logs[::-1])
            st.text_area("Logs de sistema", value=log_content, height=300, disabled=True)
        else:
            st.write("No hay eventos registrados.")

# --- PESTAÑA 2: APUESTA MAESTRA ---
with tab2:
    st.subheader("Fase 2: Validación de la Guillotina")
    cm1, cm2 = st.columns([1, 1])
    with cm1:
        m_text = st.text_area("Texto del Franco-Tirador (P2)", height=250)
    with cm2:
        m_img = st.file_uploader("Estadísticas del Partido Maestro", type=["jpg", "png", "jpeg"], key="master_img")
    
    if st.button("▶ VALIDAR APUESTA MAESTRA"):
        if not GEMINI_API_KEY:
            st.error("API Key requerida.")
        elif m_text and m_img:
            with st.status("🔍 Verificando selección final...", expanded=True):
                add_log("Iniciando auditoría de Apuesta Maestra...", "info")
                prompt = f"""
                Analiza primero si la imagen es de estadísticas deportivas reales. Si no lo es, devuelve partido: 'ERROR'. 
                Si es válida, audita el pronóstico: {m_text} contra la imagen y devuelve JSON con tipo: 'Maestra'.
                """
                partes = [prompt, {"mime_type": "image/png", "data": m_img.getvalue()}]
                res_raw, err = call_gemini_with_retry(model_option, partes)
                
                if not err:
                    try:
                        datos_maestros = json.loads(res_raw)
                        item = datos_maestros[0] if isinstance(datos_maestros, list) else datos_maestros
                        
                        if item.get('partido') == "ERROR":
                            st.error("La imagen proporcionada no es válida para la auditoría maestra.")
                            add_log("Validación fallida en Maestra.", "warning")
                        else:
                            supabase.table("auditoria_apuestas").insert(item).execute()
                            st.balloons()
                            st.success("✅ Apuesta Maestra auditada y guardada.")
                            add_log("Apuesta Maestra guardada con éxito.", "success")
                    except Exception as e:
                        st.error("Error en formato de respuesta.")
                        add_log(f"Error JSON Maestra: {str(e)}", "error")
                else:
                    st.error(err)
                    add_log(f"Fallo en Maestra: {err}", "error")

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
            st.info("Sin registros en la base de datos.")
    except Exception as e:
        st.error(f"Error de base de datos.")
        add_log(f"Error DB: {str(e)}", "error")

st.sidebar.caption("Quant/Sharp v7.6 | Validación Activa")
