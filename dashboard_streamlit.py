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
    page_title="Quant/Sharp Auditor Pro v5.9",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (LOOK PREMIUM + ANIMACIÓN DE CARGA) ---
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
    /* Animación de pulso para la carga */
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
GEMINI_API_KEY = "AIzaSyDkjIDZOMeISbINKYV6qprTFuW_GWpCvqU"

# MODELO CORREGIDO PARA PRODUCCIÓN (STREAMLIT CLOUD)
MODEL_NAME = "gemini-1.5-flash"

genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================
def extract_json(text):
    """Extrae bloques JSON de una respuesta de texto, incluso si tiene markdown"""
    list_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    if list_match:
        return list_match.group()
    obj_match = re.search(r'\{.*\}', text, re.DOTALL)
    if obj_match:
        return obj_match.group()
    return None

# =====================================================================
# MOTOR DE IA - CRUCE DE DATOS Y EMPAREJAMIENTO INTELIGENTE
# =====================================================================
def auditar_lote_informes(lista_pdfs, lista_imagenes):
    """Procesa múltiples informes e imágenes, emparejándolos automáticamente"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        # Construimos la lista de partes para el mensaje
        partes_contenido = [
            """
            [ROL] Auditor Jefe de Datos Deportivos.
            [TAREA]
            1. EMPAREJAMIENTO: Identifica qué imagen corresponde a qué PDF basándote estrictamente en los nombres de los equipos.
            2. AUDITORÍA: Compara la Fase 2 (Simulación) del PDF contra los resultados reales de la imagen.
            3. MÉTRICAS: Extrae Goles, Corners, Tarjetas, Posesión, Tiros al arco y Penales.
            
            [REGLA DE ORO] RESPONDE EXCLUSIVAMENTE CON UNA LISTA JSON. NO AGREGUES TEXTO ANTES NI DESPUÉS.
            
            Formato de la lista:
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
                "sim_goles": "Rango proyectado",
                "sim_corners": "Rango proyectado",
                "exactitud_sim": "XX%",
                "analisis_tecnico": "Tabla comparativa Markdown",
                "tipo": "Individual"
              }
            ]
            """
        ]

        # Añadimos los PDFs
        for pdf in lista_pdfs:
            partes_contenido.append({
                "mime_type": "application/pdf",
                "data": pdf.getvalue()
            })
            
        # Añadimos las Imágenes
        for img in lista_imagenes:
            partes_contenido.append({
                "mime_type": "image/png",
                "data": img.getvalue()
            })

        response = model.generate_content(partes_contenido)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def auditar_apuesta_maestra(texto_master, img_real_master):
    """Auditoría Crítica de la Selección Final (Prompt 2 - FRANCO-TIRADOR)"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = f"""
        [ROL] Auditor Jefe de Riesgos (FRANCO-TIRADOR v5.0).
        [TEXTO DEL PRONÓSTICO]: {texto_master}
        
        [TAREA] Verifica la 'APUESTA MAESTRA' y la 'RECOMENDACIÓN SECUNDARIA' contra la imagen real proporcionada.
        
        [REGLA] RESPONDE EXCLUSIVAMENTE CON UN OBJETO JSON.
        
        {{"partido": "text", "pronostico": "Mercado elegido", "marcador_final": "text", "goles_totales": int, "corners": int, "tarjetas": int, "posesion": "text", "estado": "🟢 o 🔴", "sim_goles": "N/A", "sim_corners": "N/A", "exactitud_sim": "100% o 0%", "analisis_tecnico": "Cruce final", "tipo": "Maestra"}}
        """
        
        partes = [
            prompt,
            {
                "mime_type": "image/png",
                "data": img_real_master.getvalue()
            }
        ]
        
        response = model.generate_content(partes)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# =====================================================================
# INTERFAZ DE USUARIO
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")
st.markdown("Protocolo de Seguridad v5.9 - Sistema Robusto de Auditoría")

tab1, tab2, tab3 = st.tabs(["📄 AUDITORÍA POR LOTES (P1)", "🛡️ APUESTA MAESTRA (P2)", "📊 PANEL DE CONTROL"])

# --- TAB 1: AUDITORÍA POR LOTES ---
with tab1:
    st.subheader("Fase 1: Control de Calidad de Simulaciones (Múltiple)")
    st.info("Sube tus informes PDF y las imágenes de resultados. El sistema emparejará los datos automáticamente.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        pdfs_batch = st.file_uploader("Subir Informes PDF", type="pdf", accept_multiple_files=True, key="up_pdfs")
    with col_b:
        imgs_batch = st.file_uploader("Subir Imágenes de Resultados", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="up_imgs")
    
    if st.button("▶ INICIAR AUDITORÍA POR LOTE"):
        if pdfs_batch and imgs_batch:
            with st.status("🚀 Procesando auditoría...", expanded=True) as status:
                st.markdown('<p class="loading-text">🧠 La IA está analizando y emparejando archivos...</p>', unsafe_allow_html=True)
                
                start_time = time.time()
                res_text = auditar_lote_informes(pdfs_batch, imgs_batch)
                
                st.markdown('<p class="loading-text">📊 Extrayendo métricas comparativas...</p>', unsafe_allow_html=True)
                
                json_str = extract_json(res_text)
                
                if json_str:
                    try:
                        resultados_lista = json.loads(json_str)
                        if isinstance(resultados_lista, dict):
                            resultados_lista = [resultados_lista]
                            
                        st.markdown(f'<p class="loading-text">💾 Guardando {len(resultados_lista)} registros...</p>', unsafe_allow_html=True)
                        
                        for item in resultados_lista:
                            supabase.table("auditoria_apuestas").insert(item).execute()
                        
                        duration = round(time.time() - start_time, 2)
                        status.update(label=f"✅ {len(resultados_lista)} auditorías completadas en {duration}s", state="complete", expanded=False)
                        st.success(f"¡Sincronización exitosa!")
                        
                        for r in resultados_lista:
                            with st.expander(f"Resultado: {r['partido']} - {r['estado']}"):
                                st.markdown(r['analisis_tecnico'])
                    except Exception as e:
                        st.error(f"Error al interpretar los datos: {e}")
                        with st.expander("Ver respuesta técnica"):
                            st.code(res_text)
                else:
                    status.update(label="❌ Fallo en la extracción", state="error")
                    st.error("No se pudo extraer información válida. Revisa la calidad de los archivos.")
                    with st.expander("Ver respuesta de la IA"):
                        st.write(res_text if res_text else "Sin respuesta del servidor.")
        else:
            st.warning("Debes cargar al menos un PDF y una Imagen.")

# --- TAB 2: APUESTA MAESTRA ---
with tab2:
    st.subheader("Fase 2: Validación del Veredicto Final")
    
    col_master1, col_master2 = st.columns([1, 1])
    with col_master1:
        master_text = st.text_area("Texto del Franco-Tirador (P2)", height=250, placeholder="🛡️ LA APUESTA MAESTRA...")
    with col_master2:
        master_img = st.file_uploader("Estadísticas del Partido Maestro", type=["jpg", "png", "jpeg"], key="up_master")
    
    if st.button("▶ VALIDAR APUESTA MAESTRA"):
        if master_text and master_img:
            with st.status("🔍 Verificando selección maestra...", expanded=True) as status:
                st.markdown('<p class="loading-text">🎯 Cruzando datos de seguridad con realidad...</p>', unsafe_allow_html=True)
                res = auditar_apuesta_maestra(master_text, master_img)
                
                json_str = extract_json(res)
                if json_str:
                    try:
                        data = json.loads(json_str)
                        supabase.table("auditoria_apuestas").insert(data).execute()
                        status.update(label="✅ Apuesta Maestra Validada", state="complete", expanded=False)
                        st.balloons()
                        st.markdown(re.sub(r'```json.*?```', '', res, flags=re.DOTALL))
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                        st.code(res)
                else:
                    status.update(label="❌ Error de formato", state="error")
                    st.error("No se detectó el JSON de respuesta.")
                    st.code(res)
        else:
            st.warning("Ingresa el texto y la imagen de resultados.")

# --- TAB 3: DASHBOARD ---
with tab3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)

        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            op_tipo = st.pills("Ver datos de:", ["Todos", "Individuales", "Apuestas Maestras"], default="Todos")
            
            df_view = df if op_tipo == "Todos" else df[df['tipo'] == ('Individual' if op_tipo == "Individuales" else 'Maestra')]

            k1, k2, k3, k4 = st.columns(4)
            total = len(df_view)
            hits = len(df_view[df_view['estado'].str.contains('🟢')])
            win_rate = (hits/total*100) if total > 0 else 0
            
            k1.metric("Análisis", total)
            k2.metric("Acierto %", f"{win_rate:.1f}%")
            k3.metric("Filtro", op_tipo)
            k4.metric("Status", "🛡️ Protegido" if win_rate > 65 else "⚖️ Estable")

            st.markdown("---")
            g1, g2 = st.columns(2)
            with g1:
                st.plotly_chart(px.pie(df_view, names='estado', hole=0.5, title="Distribución",
                                     color='estado', color_discrete_map={'🟢':'#2ea043','🔴':'#da3633'}), use_container_width=True)
            with g2:
                df_view['val'] = df_view['estado'].apply(lambda x: 1 if '🟢' in x else 0)
                st.plotly_chart(px.line(df_view.sort_values('fecha'), x='fecha', y='val', markers=True, title="Evolución"), use_container_width=True)

            st.subheader("Historial Completo")
            st.dataframe(df_view[['fecha', 'partido', 'pronostico', 'estado', 'tipo', 'analisis_tecnico']], use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

st.sidebar.caption("Quant/Sharp v5.9 | Franco-Tirador Workflow")
