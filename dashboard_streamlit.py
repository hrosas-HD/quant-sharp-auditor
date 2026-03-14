import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import re
import json
import time

# =====================================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Quant/Sharp Auditor Pro v6.2",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
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
        font-size: 1.2rem;
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
    div[data-testid="stExpander"] {
        background-color: #161b22;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"

# CONFIGURACIÓN DE SEGURIDAD ACTUALIZADA
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    # Usamos la nueva clave proporcionada (asegúrate de haberla creado en Google AI Studio)
    GEMINI_API_KEY = "AIzaSyCpeJM5HYnJuzH8YH1OG5lZ4D7BE4bTcTQ"

MODEL_NAME = "gemini-1.5-flash"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================
def extract_json(text):
    """Extrae y limpia bloques JSON de una respuesta de texto"""
    try:
        # Intentar parsear directamente si el texto es JSON puro
        return json.loads(text)
    except:
        # Si falla, buscar bloques marcados con markdown o llaves
        list_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if list_match:
            try: return json.loads(list_match.group())
            except: pass
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        if obj_match:
            try: return json.loads(obj_match.group())
            except: pass
    return None

# =====================================================================
# MOTOR DE IA - CRUCE DE DATOS
# =====================================================================
def auditar_lote_informes(lista_pdfs, lista_imagenes):
    if not GEMINI_API_KEY:
        return "Error: No se ha configurado la clave de API de Gemini."
    
    try:
        # Configuración para forzar salida JSON válida
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = """
        [ROL] Auditor Jefe de Datos Deportivos Pro.
        [TAREA]
        1. EMPAREJAMIENTO: Identifica qué imagen corresponde a qué PDF basándote en los nombres de los equipos.
        2. AUDITORÍA FASE 2: Compara la Simulación del PDF contra los resultados reales de la imagen.
        3. MÉTRICAS EXHAUSTIVAS: Extrae Goles, Corners, Tarjetas, Posesión, Tiros al arco y Penales.
        
        [REGLA] RESPONDE EXCLUSIVAMENTE CON UNA LISTA DE OBJETOS JSON. 
        Asegúrate de que todos los nombres de propiedades estén entre comillas dobles.
        
        Formato de salida requerido:
        [
          {
            "partido": "Nombre exacto",
            "pronostico": "Resumen recomendaciones",
            "marcador_final": "Resultado real",
            "goles_totales": int,
            "corners": int,
            "tarjetas": int,
            "posesion": "XX%",
            "estado": "🟢 (Acierto) o 🔴 (Fallo)",
            "sim_goles": "Rango proyectado Fase 2",
            "sim_corners": "Rango proyectado Fase 2",
            "exactitud_sim": "XX%",
            "analisis_tecnico": "Tabla comparativa Markdown de todas las estadísticas",
            "tipo": "Individual"
          }
        ]
        """

        partes_contenido = [prompt]
        for pdf in lista_pdfs:
            partes_contenido.append({"mime_type": "application/pdf", "data": pdf.getvalue()})
        for img in lista_imagenes:
            partes_contenido.append({"mime_type": "image/png", "data": img.getvalue()})

        response = model.generate_content(partes_contenido)
        return response.text
    except Exception as e:
        return f"Error en la llamada al modelo: {str(e)}"

def auditar_apuesta_maestra(texto_master, img_real_master):
    if not GEMINI_API_KEY:
        return "Error: API Key de Gemini no encontrada."

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = f"""
        [ROL] Auditor Jefe de Riesgos (FRANCO-TIRADOR v5.0).
        [PRONÓSTICO]: {texto_master}
        [TAREA] Verifica 'APUESTA MAESTRA' y 'RECOMENDACIÓN SECUNDARIA' contra la imagen real.
        [REGLA] RESPONDE EXCLUSIVAMENTE CON UN OBJETO JSON VÁLIDO.
        
        Formato:
        {{"partido": "text", "pronostico": "Mercado", "marcador_final": "text", "goles_totales": int, "corners": int, "tarjetas": int, "posesion": "text", "estado": "🟢 o 🔴", "sim_goles": "N/A", "sim_corners": "N/A", "exactitud_sim": "100% o 0%", "analisis_tecnico": "Análisis", "tipo": "Maestra"}}
        """
        
        partes = [prompt, {"mime_type": "image/png", "data": img_real_master.getvalue()}]
        response = model.generate_content(partes)
        return response.text
    except Exception as e:
        return f"Error en la llamada al modelo: {str(e)}"

# =====================================================================
# INTERFAZ DE USUARIO
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")
st.markdown(f"Protocolo de Seguridad v6.2 - Flujo Franco-Tirador Activo")

if not GEMINI_API_KEY:
    st.error("⚠️ **API Key no configurada.** Por favor, agrégala en los Secrets de Streamlit.")

tab1, tab2, tab3 = st.tabs(["📄 AUDITORÍA POR LOTES (P1)", "🛡️ APUESTA MAESTRA (P2)", "📊 PANEL DE CONTROL"])

with tab1:
    st.subheader("Fase 1: Auditoría de Informes Individuales")
    st.info("Sube tus informes PDF y las imágenes de resultados para el emparejamiento automático.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        pdfs_batch = st.file_uploader("Subir Informes PDF", type="pdf", accept_multiple_files=True, key="up_pdfs")
    with col_b:
        imgs_batch = st.file_uploader("Subir Imágenes de Resultados", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="up_imgs")
    
    if st.button("▶ INICIAR AUDITORÍA POR LOTE"):
        if not GEMINI_API_KEY:
            st.error("Falta API Key.")
        elif pdfs_batch and imgs_batch:
            with st.status("🚀 Analizando partidos...", expanded=True) as status:
                st.markdown('<p class="loading-text">🧠 La IA está cruzando datos de Simulación vs Realidad...</p>', unsafe_allow_html=True)
                
                start_time = time.time()
                res_text = auditar_lote_informes(pdfs_batch, imgs_batch)
                
                # Intentar interpretar los datos directamente con la nueva función robusta
                datos_interpretados = extract_json(res_text)
                
                if datos_interpretados:
                    try:
                        # Convertir a lista si es un solo objeto
                        if isinstance(datos_interpretados, dict):
                            resultados_lista = [datos_interpretados]
                        else:
                            resultados_lista = datos_interpretados
                            
                        for item in resultados_lista:
                            supabase.table("auditoria_apuestas").insert(item).execute()
                        
                        duration = round(time.time() - start_time, 2)
                        status.update(label=f"✅ {len(resultados_lista)} auditorías completadas en {duration}s", state="complete", expanded=False)
                        st.success(f"¡Sincronización exitosa!")
                        
                        for r in resultados_lista:
                            with st.expander(f"Resultado: {r['partido']} - {r['estado']}"):
                                st.markdown(r['analisis_tecnico'])
                    except Exception as e:
                        st.error(f"Error al guardar datos en Supabase: {e}")
                else:
                    status.update(label="❌ Error de formato JSON", state="error")
                    st.error("La IA devolvió datos en un formato que no pudo ser procesado automáticamente.")
                    with st.expander("Ver respuesta técnica (Depuración)"):
                        st.write(res_text)
        else:
            st.warning("Debes cargar al menos un PDF y una Imagen.")

with tab2:
    st.subheader("Fase 2: Validación de Apuesta Maestra")
    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        m_text = st.text_area("Resultado del Prompt 2 (Texto)", height=250)
    with col_m2:
        m_img = st.file_uploader("Captura de Estadísticas Finales", type=["jpg", "png", "jpeg"], key="up_m")
    
    if st.button("▶ VALIDAR APUESTA MAESTRA"):
        if m_text and m_img:
            with st.status("🔍 Validando selección del Franco-Tirador...", expanded=True) as status:
                st.markdown('<p class="loading-text">🎯 Verificando si se protegió el capital...</p>', unsafe_allow_html=True)
                res = auditar_apuesta_maestra(m_text, m_img)
                
                datos_maestros = extract_json(res)
                if datos_maestros:
                    try:
                        supabase.table("auditoria_apuestas").insert(datos_maestros).execute()
                        status.update(label="✅ Apuesta Maestra Validada", state="complete")
                        st.balloons()
                        st.markdown("### Reporte Final de Apuesta Maestra")
                        st.markdown(datos_maestros.get("analisis_tecnico", "Sin detalles adicionales."))
                    except Exception as e:
                        st.error(f"Error al guardar en Supabase: {e}")
                else:
                    st.error("Error de formato en la respuesta de la IA.")
                    with st.expander("Depuración"):
                        st.code(res)

with tab3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)

        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            op_tipo = st.pills("Ver datos de:", ["Todos", "Individuales", "Apuestas Maestras"], default="Todos")
            df_view = df if op_tipo == "Todos" else df[df['tipo'] == ('Individual' if op_tipo == "Individuales" else 'Maestra')]

            k1, k2, k3 = st.columns(3)
            k1.metric("Análisis", len(df_view))
            hits = len(df_view[df_view['estado'].str.contains('🟢')])
            win_rate = (hits/len(df_view)*100 if len(df_view)>0 else 0)
            k2.metric("Acierto %", f"{win_rate:.1f}%")
            k3.metric("Estatus", "🛡️ Protegido" if win_rate > 65 else "⚖️ Estable")

            st.plotly_chart(px.pie(df_view, names='estado', hole=0.5, title="Distribución de Resultados"), use_container_width=True)
            st.subheader("Historial Completo")
            st.dataframe(df_view[['fecha', 'partido', 'pronostico', 'estado', 'tipo', 'analisis_tecnico']], use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros en la base de datos.")
    except Exception as e:
        st.error(f"Error de conexión con Supabase: {e}")

st.sidebar.caption("Quant/Sharp v6.2 | Franco-Tirador Workflow")
