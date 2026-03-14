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
    page_title="Quant/Sharp Auditor Pro v5.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (LOOK PREMIUM) ---
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
# MOTOR DE IA - CRUCE DE DATOS MULTI-FUENTE
# =====================================================================
def auditar_informe_individual(pdf_sim, img_real):
    """Compara un informe PDF individual (Prompt 1) con su resultado real"""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        pdf_parts = [{"mime_type": "application/pdf", "data": pdf_sim.getvalue()}]
        real_parts = [{"mime_type": "image/jpeg", "data": img_real.getvalue()}]

        prompt = """
        [ROL] Auditor de Simulación Pro (Fase 2 vs Realidad).
        [TAREA] Analiza la FASE 2 del PDF (Simulación) y compárala con las estadísticas reales de la Imagen.
        
        [MÉTRICAS A EXTRAER Y COMPARAR]
        Extrae obligatoriamente estos datos de AMBAS fuentes (si están disponibles):
        1. Goles (Marcador).
        2. Tiros de Esquina (Corners).
        3. Tarjetas (Amarillas/Rojas).
        4. Posesión de Balón (%).
        5. Tiros al Arco (Shots on Target).
        6. Penales (Concedidos/Anotados).
        
        [ANÁLISIS]
        - Compara los rangos proyectados en la simulación contra el dato real exacto.
        - Evalúa si el análisis del Prompt 1 fue acertado en su lectura de la dinámica del partido.
        
        Devuelve un JSON:
        {
          "partido": "Nombre de los equipos",
          "pronostico": "Resumen de recomendaciones del informe PDF",
          "marcador_final": "Resultado final",
          "goles_totales": int,
          "corners": int,
          "tarjetas": int,
          "posesion": "text %",
          "estado": "🟢 (Simulación acertada) / 🔴 (Desviación crítica)",
          "sim_goles": "Rango proyectado en Fase 2",
          "sim_corners": "Rango proyectado en Fase 2",
          "exactitud_sim": "Cálculo técnico de precisión %",
          "analisis_tecnico": "Tabla comparativa Markdown detallada: Goles, Corners, Tarjetas, Posesión, Tiros al arco y Penales (Simulado vs Real)",
          "tipo": "Individual"
        }
        """
        response = model.generate_content([*pdf_parts, *real_parts, prompt])
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
        
        [TAREA] 
        1. Identifica 'LA APUESTA MAESTRA' y su mercado.
        2. Identifica la 'RECOMENDACIÓN SECUNDARIA (CÓRNERS)'.
        3. Contrasta AMBAS selecciones con la Imagen Real (Goles, Corners, Tarjetas, Tiros al arco, Penales).
        
        [VERDICTO]
        Determina si la Apuesta Maestra fue ganada. Menciona también si el mercado de corners se acertó y si la lectura de seguridad fue correcta frente a las estadísticas reales.
        
        Devuelve un JSON:
        {"partido": "text", "pronostico": "Mercado Apuesta Maestra", "marcador_final": "text", "goles_totales": int, "corners": int, "tarjetas": int, "posesion": "text", "estado": "🟢 (Ganada) / 🔴 (Perdida)", "sim_goles": "N/A", "sim_corners": "N/A", "exactitud_sim": "100% o 0%", "analisis_tecnico": "Resumen de acierto de Maestra + Córners. Comparativa de estadísticas clave (Tiros, Penales, etc.)", "tipo": "Maestra"}
        """
        response = model.generate_content([*real_parts, prompt])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# =====================================================================
# INTERFAZ DE USUARIO
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")
st.markdown("Protocolo de Seguridad v5.0 - Auditoría de Selección Única")

tab1, tab2, tab3 = st.tabs(["📄 AUDITORÍA DE INFORMES (P1)", "🛡️ APUESTA MAESTRA (P2)", "📊 PANEL DE CONTROL"])

# --- TAB 1: AUDITORÍA DE CADA PDF (PROMPT 1) ---
with tab1:
    st.subheader("Fase 1: Control de Calidad de Simulaciones")
    st.info("Sube cada informe PDF (Prompt 1) para comparar la Fase 2 (Goles, Corners, Tarjetas, Tiros, Penales) contra la realidad.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        pdf_ind = st.file_uploader("Subir Informe PDF del Partido", type="pdf", key="up_pdf")
    with col_b:
        img_ind = st.file_uploader("Subir Resultado Real", type=["jpg", "png", "jpeg"], key="up_img_ind")
    
    if st.button("▶ ANALIZAR INFORME INDIVIDUAL"):
        if pdf_ind and img_ind:
            with st.status("Auditando Simulación Fase 2...") as status:
                res = auditar_informe_individual(pdf_ind, img_ind)
                json_match = re.search(r'\{.*\}', res, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    supabase.table("auditoria_apuestas").insert(data).execute()
                    status.update(label="✅ Informe Individual Auditado", state="complete")
                    st.markdown(re.sub(r'```json.*?```', '', res, flags=re.DOTALL))
        else:
            st.warning("Se requiere PDF y captura de resultados.")

# --- TAB 2: APUESTA MAESTRA (PROMPT 2) ---
with tab2:
    st.subheader("Fase 2: Validación del Veredicto Final")
    st.markdown("#### *'Proteger el capital es la única prioridad.'*")
    
    col_master1, col_master2 = st.columns([1, 1])
    with col_master1:
        st.markdown("**Resultado del Prompt 2 (Texto)**")
        master_text = st.text_area("Pega aquí el reporte del Franco-Tirador...", height=300, placeholder="🛡️ LA APUESTA MAESTRA...")
    
    with col_master2:
        st.markdown("**Resultado Real del Partido Elegido**")
        master_img = st.file_uploader("Subir Estadísticas del Partido Maestro", type=["jpg", "png", "jpeg"], key="up_master")
    
    if st.button("▶ VALIDAR APUESTA MAESTRA v5.0"):
        if master_text and master_img:
            with st.status("Ejecutando Guillotina de Verificación...") as status:
                res = auditar_apuesta_maestra(master_text, master_img)
                json_match = re.search(r'\{.*\}', res, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    supabase.table("auditoria_apuestas").insert(data).execute()
                    status.update(label="✅ Apuesta Maestra Registrada", state="complete")
                    st.balloons()
                    st.markdown("### 🏆 Veredicto de la IA sobre tu Apuesta Maestra")
                    st.markdown(re.sub(r'```json.*?```', '', res, flags=re.DOTALL))
        else:
            st.warning("Pega el texto de la selección maestra y sube la imagen del resultado.")

# --- TAB 3: DASHBOARD DE RENDIMIENTO ---
with tab3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)

        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            # Filtro por Tipo de Operación
            st.markdown("### Rendimiento por Segmento")
            op_tipo = st.pills("Filtrar Auditorías:", ["Todos", "Individuales", "Apuestas Maestras"], default="Todos")
            
            if op_tipo == "Individuales":
                df_view = df[df['tipo'] == 'Individual']
            elif op_tipo == "Apuestas Maestras":
                df_view = df[df['tipo'] == 'Maestra']
            else:
                df_view = df

            # KPIs de Backtesting
            k1, k2, k3, k4 = st.columns(4)
            total = len(df_view)
            hits = len(df_view[df_view['estado'].str.contains('🟢')])
            win_rate = (hits/total*100) if total > 0 else 0
            
            k1.metric("Auditorías", total)
            k2.metric("Tasa de Acierto", f"{win_rate:.1f}%")
            k3.metric("Segmento", op_tipo)
            k4.metric("Status", "🛡️ Protegido" if win_rate > 60 else "⚠️ Revisar Filtros")

            st.markdown("---")
            
            # Gráficas
            g1, g2 = st.columns(2)
            with g1:
                st.plotly_chart(px.pie(df_view, names='estado', hole=0.5, title="Distribución de Resultados",
                                     color='estado', color_discrete_map={'🟢':'#2ea043','🔴':'#da3633'}), use_container_width=True)
            with g2:
                # Evolución de acierto
                df_view['hit_val'] = df_view['estado'].apply(lambda x: 1 if '🟢' in x else 0)
                fig_evol = px.line(df_view.sort_values('fecha'), x='fecha', y='hit_val', markers=True, title="Histórico de Acierto (1=Win, 0=Loss)")
                st.plotly_chart(fig_evol, use_container_width=True)

            st.subheader("Detalle del Backtesting")
            st.dataframe(
                df_view[['fecha', 'partido', 'pronostico', 'estado', 'tipo', 'analisis_tecnico']],
                column_config={
                    "analisis_tecnico": st.column_config.TextColumn("Análisis de Coherencia", width="large")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Inicia el flujo auditando tus primeros partidos.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

st.sidebar.caption("Quant/Sharp v5.0 | Workflow Franco-Tirador")
