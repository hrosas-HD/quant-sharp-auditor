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
    page_title="Quant/Sharp Auditor Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (LOOK PREMIUM) ---
st.markdown("""
    <style>
    /* Fondo principal y fuentes */
    .main { background-color: #0e1117; }
    
    /* Contenedores de Métricas */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Títulos y Subtítulos */
    h1, h2, h3 { color: #f0f6fc; font-weight: 700; }
    
    /* Botones */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #238636;
        color: white;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2ea043;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(46, 160, 67, 0.4);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: white !important;
        border-color: #1f6feb !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"
GEMINI_API_KEY = "AIzaSyDkjIDZOMeISbINKYV6qprTFuW_GWpCvqU"

genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# MOTOR DE AUDITORÍA (IA) - AHORA CON 3 ENTRADAS
# =====================================================================
def procesar_con_ia(pdf_sim, img_bet, img_real):
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        # Preparar los 3 archivos
        pdf_parts = [{"mime_type": "application/pdf", "data": pdf_sim.getvalue()}]
        bet_parts = [{"mime_type": "image/jpeg", "data": img_bet.getvalue()}]
        real_parts = [{"mime_type": "image/jpeg", "data": img_real.getvalue()}]

        prompt = """
        [ROL] Auditor Cuantitativo Deportivo Profesional.
        [TAREA] Realiza un cruce de datos entre 3 fuentes de información.
        
        1. FUENTE A (PDF Simulación): Extrae los rangos proyectados de goles, corners y tarjetas.
        2. FUENTE B (Imagen Apuesta): Identifica qué se apostó exactamente (ej: Over 2.5 goles).
        3. FUENTE C (Imagen Realidad): Extrae los resultados finales del partido.

        [ANÁLISIS]
        - ¿La apuesta (Fuente B) fue coherente con la simulación (Fuente A)?
        - ¿Se ganó la apuesta según los resultados reales (Fuente C)?
        - ¿Qué porcentaje de precisión tuvo la simulación frente a la realidad?

        [SALIDA] Genera un reporte técnico y devuelve un JSON con este formato exacto:
        {"partido": "text", "pronostico": "text (lo que se apostó)", "marcador_final": "text", "goles_totales": int, "corners": int, "tarjetas": int, "posesion": "text", "estado": "🟢 (Ganada) / 🔴 (Perdida) / ⚪ (Void)", "sim_goles": "rango proyectado", "sim_corners": "rango proyectado", "exactitud_sim": "text %", "analisis_tecnico": "text explicando el cruce de las 3 fuentes"}
        """
        
        response = model.generate_content([*pdf_parts, *bet_parts, *real_parts, prompt])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# =====================================================================
# BARRA LATERAL (SIDEBAR)
# =====================================================================
with st.sidebar:
    st.image("https://www.google.com/s2/favicons?domain=supabase.com&sz=128", width=60)
    st.title("Configuración")
    st.write("Gestiona tu entorno de auditoría.")
    
    if st.button("🔄 Refrescar Datos"):
        st.rerun()
    
    st.divider()
    st.info("💡 **Flujo Correcto:** Sube primero la Simulación, luego tu Ticket de Apuesta y finalmente los Resultados.")
    st.caption("v3.5 Multimodal | Quant/Sharp Pro")

# =====================================================================
# CUERPO PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")
st.markdown("Plataforma de Verificación de Estrategias: Simulación vs. Apuesta vs. Realidad.")

tab_audit, tab_stats = st.tabs(["🚀 EJECUTAR AUDITORÍA", "📊 DASHBOARD & HISTORIAL"])

# --- PESTAÑA 1: EJECUCIÓN ---
with tab_audit:
    st.subheader("Carga de Evidencia Triple")
    
    # Diseño en 3 columnas para los 3 archivos
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. Simulación (PDF)**")
        pdf_up = st.file_uploader("Subir Fase 2", type="pdf", label_visibility="collapsed", key="pdf")
    with c2:
        st.markdown("**2. Tu Apuesta (Imagen)**")
        bet_up = st.file_uploader("Subir Ticket/Selección", type=["jpg", "png", "jpeg"], label_visibility="collapsed", key="bet")
    with c3:
        st.markdown("**3. Resultados (Imagen)**")
        real_up = st.file_uploader("Subir Estadísticas Finales", type=["jpg", "png", "jpeg"], label_visibility="collapsed", key="real")
    
    st.markdown("---")
    
    if st.button("▶ INICIAR AUDITORÍA INTEGRAL"):
        if pdf_up and bet_up and real_up:
            with st.status("🧠 Cruzando Simulación, Apuesta y Realidad...", expanded=True) as status:
                resultado = procesar_con_ia(pdf_up, bet_up, real_up)
                
                json_match = re.search(r'\{.*\}', resultado, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        supabase.table("auditoria_apuestas").insert(data).execute()
                        status.update(label="✅ Auditoría de 3 Vías Completada", state="complete")
                        
                        st.balloons()
                        
                        col_rep1, col_rep2 = st.columns([1, 2])
                        with col_rep1:
                            st.success(f"**Resultado Apuesta:** {data['estado']}")
                            st.metric("Precisión Modelo", data['exactitud_sim'])
                        with col_rep2:
                            st.markdown(f"### Selección Realizada: {data['pronostico']}")
                            st.write(data['analisis_tecnico'])
                        
                        st.divider()
                        st.markdown("#### Análisis Detallado de Coherencia")
                        st.markdown(re.sub(r'```json.*?```', '', resultado, flags=re.DOTALL))
                        
                    except Exception as e:
                        st.error(f"Error al sincronizar datos: {e}")
                else:
                    st.error("La IA no pudo procesar el cruce de las 3 imágenes. Verifica la calidad de las capturas.")
        else:
            st.warning("Se requieren los 3 archivos para una auditoría completa (PDF, Ticket y Estadísticas).")

# --- PESTAÑA 2: ESTADÍSTICAS ---
with tab_stats:
    try:
        res = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(res.data)

        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['exactitud_val'] = df['exactitud_sim'].str.replace('%', '').astype(float)
            
            st.markdown("### Filtros de Análisis")
            f1, f2 = st.columns([2, 1])
            with f1:
                search = st.text_input("🔍 Buscar por equipo...", "")
            with f2:
                estados = st.multiselect("Estado de Apuesta", options=df['estado'].unique(), default=df['estado'].unique())
            
            mask = df['estado'].isin(estados)
            if search:
                mask = mask & df['partido'].str.contains(search, case=False)
            
            filtered_df = df[mask]

            st.write("")
            k1, k2, k3, k4 = st.columns(4)
            total = len(filtered_df)
            wins = len(filtered_df[filtered_df['estado'].str.contains('🟢')])
            win_rate = (wins/total*100) if total > 0 else 0
            
            k1.metric("Auditorías", total)
            k2.metric("Yield Estimado (Acierto)", f"{win_rate:.1f}%")
            k3.metric("Exactitud Media Sim", f"{filtered_df['exactitud_val'].mean():.1f}%")
            k4.metric("Consistencia", "💎 Alta" if win_rate > 65 else "⚖️ Estable")

            st.markdown("---")
            
            g1, g2 = st.columns([1, 1.5])
            with g1:
                fig_pie = px.pie(
                    filtered_df, names='estado', hole=0.6,
                    color='estado', 
                    title="Balance de Apuestas Reales"
                )
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#8b949e", showlegend=False
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with g2:
                fig_line = px.line(
                    filtered_df.sort_values('fecha'), x='fecha', y='exactitud_val',
                    title="Calidad de las Simulaciones en el Tiempo",
                    markers=True, line_shape="spline"
                )
                fig_line.update_traces(line_color='#1f6feb', marker_size=8)
                fig_line.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#8b949e", xaxis_title="", yaxis_title="Exactitud %"
                )
                st.plotly_chart(fig_line, use_container_width=True)

            st.subheader("📋 Registro de Auditoría de 3 Vías")
            st.dataframe(
                filtered_df[['fecha', 'partido', 'pronostico', 'marcador_final', 'estado', 'exactitud_sim', 'analisis_tecnico']],
                column_config={
                    "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YY HH:mm"),
                    "pronostico": st.column_config.TextColumn("Apuesta Realizada", width="medium"),
                    "estado": st.column_config.TextColumn("Status", width="small"),
                    "analisis_tecnico": st.column_config.TextColumn("Análisis de Coherencia", width="large")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay registros. Sube la Simulación + Apuesta + Realidad para comenzar.")
    except Exception as e:
        st.error(f"Error al conectar con los datos: {e}")

st.divider()
st.caption("Quant/Sharp Auditor Pro - Análisis de coherencia estratégica Multimodal.")
