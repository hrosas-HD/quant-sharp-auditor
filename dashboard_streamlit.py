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
    page_title="Quant/Sharp Auditor Pro v5.6",
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

genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# MOTOR DE IA - CRUCE DE DATOS Y EMPAREJAMIENTO INTELIGENTE
# =====================================================================
def auditar_lote_informes(lista_pdfs, lista_imagenes):
    """Procesa múltiples informes e imágenes, emparejándolos automáticamente"""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        archivos_ia = []
        for pdf in lista_pdfs:
            archivos_ia.append({"mime_type": "application/pdf", "data": pdf.getvalue()})
        for img in lista_imagenes:
            archivos_ia.append({"mime_type": "image/jpeg", "data": img.getvalue()})

        prompt = """
        [ROL] Auditor Jefe de Datos Deportivos.
        [TAREA]
        1. EMPAREJAMIENTO: Lee el contenido de cada PDF y cada imagen. Identifica qué imagen corresponde a qué PDF.
        2. AUDITORÍA INDIVIDUAL: Compara la Simulación (Fase 2) contra la Realidad.
        3. MÉTRICAS: Extrae Goles, Corners, Tarjetas, Posesión, Tiros al arco y Penales.
        
        Devuelve una LISTA JSON:
        [
          {
            "partido": "Equipo A vs Equipo B",
            "pronostico": "Recomendaciones del PDF",
            "marcador_final": "Resultado",
            "goles_totales": int,
            "corners": int,
            "tarjetas": int,
            "posesion": "text %",
            "estado": "🟢/🔴",
            "sim_goles": "Rango Fase 2",
            "sim_corners": "Rango Fase 2",
            "exactitud_sim": "text %",
            "analisis_tecnico": "Tabla comparativa de todas las métricas",
            "tipo": "Individual"
          }
        ]
        """
        response = model.generate_content([*archivos_ia, prompt])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def auditar_apuesta_maestra(texto_master, img_real_master):
    """Auditoría Crítica de la Selección Final (Prompt 2 - FRANCO-TIRADOR)"""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        real_parts = [{"mime_type": "image/jpeg", "data": img_real_master.getvalue()}]

        prompt = f"""
        [ROL] Auditor Jefe de Riesgos (FRANCO-TIRADOR v5.0).
        [CONTEXTO - RESULTADO PROMPT 2]: {texto_master}
        [TAREA] Verifica la 'APUESTA MAESTRA' y la 'RECOMENDACIÓN SECUNDARIA' contra la Imagen Real.
        
        Devuelve un JSON:
        {"partido": "text", "pronostico": "Mercado Apuesta Maestra", "marcador_final": "text", "goles_totales": int, "corners": int, "tarjetas": int, "posesion": "text", "estado": "🟢 (Ganada) / 🔴 (Perdida)", "sim_goles": "N/A", "sim_corners": "N/A", "exactitud_sim": "100% o 0%", "analisis_tecnico": "Cruce técnico final", "tipo": "Maestra"}
        """
        response = model.generate_content([*real_parts, prompt])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# =====================================================================
# INTERFAZ DE USUARIO
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")
st.markdown("Protocolo de Seguridad v5.6 - Centro de Auditoría Inteligente")

tab1, tab2, tab3 = st.tabs(["📄 AUDITORÍA POR LOTES (P1)", "🛡️ APUESTA MAESTRA (P2)", "📊 PANEL DE CONTROL"])

# --- TAB 1: AUDITORÍA POR LOTES ---
with tab1:
    st.subheader("Fase 1: Control de Calidad de Simulaciones (Múltiple)")
    st.info("Sube todos tus informes PDF y las imágenes de resultados para el emparejamiento automático.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        pdfs_batch = st.file_uploader("Subir Informes PDF", type="pdf", accept_multiple_files=True, key="up_pdfs")
    with col_b:
        imgs_batch = st.file_uploader("Subir Imágenes de Resultados", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="up_imgs")
    
    if st.button("▶ INICIAR AUDITORÍA POR LOTE"):
        if pdfs_batch and imgs_batch:
            # Iniciamos el contenedor de estado con visualización de carga
            with st.status("🚀 Iniciando proceso de auditoría...", expanded=True) as status:
                st.markdown('<p class="loading-text">🧠 La IA está leyendo y emparejando archivos...</p>', unsafe_allow_html=True)
                
                start_time = time.time()
                res_text = auditar_lote_informes(pdfs_batch, imgs_batch)
                
                st.markdown('<p class="loading-text">📊 Comparando métricas (Goles, Corners, Tiros)...</p>', unsafe_allow_html=True)
                
                json_match = re.search(r'\[\s*\{.*\}\s*\]', res_text, re.DOTALL)
                if json_match:
                    try:
                        resultados_lista = json.loads(json_match.group())
                        st.markdown(f'<p class="loading-text">💾 Guardando {len(resultados_lista)} resultados en la nube...</p>', unsafe_allow_html=True)
                        
                        for item in resultados_lista:
                            supabase.table("auditoria_apuestas").insert(item).execute()
                        
                        duration = round(time.time() - start_time, 2)
                        status.update(label=f"✅ {len(resultados_lista)} partidos auditados en {duration}s", state="complete", expanded=False)
                        st.success(f"¡Procesamiento completo! Se han sincronizado {len(resultados_lista)} registros.")
                        
                        for r in resultados_lista:
                            with st.expander(f"Auditoría: {r['partido']} - {r['estado']}"):
                                st.markdown(r['analisis_tecnico'])
                    except Exception as e:
                        st.error(f"Error al procesar: {e}")
                else:
                    status.update(label="❌ Error en el emparejamiento", state="error")
                    st.error("No se pudo extraer información válida. Revisa la calidad de los archivos.")
        else:
            st.warning("Carga los archivos antes de ejecutar.")

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
            with st.status("🔍 Verificando apuesta maestra...", expanded=True) as status:
                st.markdown('<p class="loading-text">🎯 Cruzando selección con estadísticas finales...</p>', unsafe_allow_html=True)
                res = auditar_apuesta_maestra(master_text, master_img)
                
                json_match = re.search(r'\{.*\}', res, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    supabase.table("auditoria_apuestas").insert(data).execute()
                    status.update(label="✅ Apuesta Maestra Validada", state="complete", expanded=False)
                    st.balloons()
                    st.markdown(re.sub(r'```json.*?```', '', res, flags=re.DOTALL))
        else:
            st.warning("Completa los campos para validar.")

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
            
            k1.metric("Partidos", total)
            k2.metric("Acierto %", f"{win_rate:.1f}%")
            k3.metric("Filtro", op_tipo)
            k4.metric("Status", "🛡️ Seguro" if win_rate > 65 else "⚖️ Estable")

            st.markdown("---")
            g1, g2 = st.columns(2)
            with g1:
                st.plotly_chart(px.pie(df_view, names='estado', hole=0.5, title="Balance Global",
                                     color='estado', color_discrete_map={'🟢':'#2ea043','🔴':'#da3633'}), use_container_width=True)
            with g2:
                df_view['val'] = df_view['estado'].apply(lambda x: 1 if '🟢' in x else 0)
                st.plotly_chart(px.line(df_view.sort_values('fecha'), x='fecha', y='val', markers=True, title="Evolución de Acierto"), use_container_width=True)

            st.subheader("Historial Completo")
            st.dataframe(df_view[['fecha', 'partido', 'pronostico', 'estado', 'tipo', 'analisis_tecnico']], use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay registros guardados.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

st.sidebar.caption("Quant/Sharp v5.6 | Franco-Tirador Workflow")
