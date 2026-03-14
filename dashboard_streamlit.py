import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import google.generativeai as genai
import re
import json
import time

# =====================================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Quant/Sharp Auditor Web",
    page_icon="🎯",
    layout="wide"
)

# Estilos visuales para modo oscuro premium
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #58a6ff; }
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        height: 3.5em; 
        background-color: #1f6feb; 
        color: white; 
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover { background-color: #388bfd; border: none; }
    </style>
    """, unsafe_allow_html=True)

# Credenciales integradas (Proyecto: tnxhmhoczcbfmhieaxgt)
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"
GEMINI_API_KEY = "AIzaSyDkjIDZOMeISbINKYV6qprTFuW_GWpCvqU"

genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# MOTOR DE AUDITORÍA (IA MULTIMODAL)
# =====================================================================
def procesar_con_ia(pdf_file, img_file):
    """Función que reemplaza a Google Colab procesando archivos directamente"""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        # Preparación de archivos para la API de Gemini
        pdf_parts = [{"mime_type": "application/pdf", "data": pdf_file.getvalue()}]
        img_parts = [{"mime_type": "image/jpeg", "data": img_file.getvalue()}]

        prompt = """
        [ROL] Auditor Cuantitativo Deportivo Profesional.
        [TAREA] Analiza el PDF (Simulación de Fase 2) y compáralo con la Imagen (Estadísticas Reales).
        1. Crea un reporte detallado comparando goles, corners y tarjetas proyectadas vs reales.
        2. Genera un bloque JSON final con estas llaves exactas para la base de datos:
        {"partido": "text", "pronostico": "text", "marcador_final": "text", "goles_totales": int, "corners": int, "tarjetas": int, "posesion": "text", "estado": "🟢/🔴/⚪", "sim_goles": "text", "sim_corners": "text", "exactitud_sim": "text", "analisis_tecnico": "text"}
        """
        
        response = model.generate_content([*pdf_parts, *img_parts, prompt])
        return response.text
    except Exception as e:
        return f"Error crítico de IA: {str(e)}"

# =====================================================================
# INTERFAZ DE USUARIO (TABS)
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")
st.write("Sistema autónomo de verificación de modelos y gestión de backtesting.")

tabs = st.tabs(["🚀 Nueva Auditoría", "📊 Panel de Control e Historial"])

with tabs[0]:
    st.header("Entrada de Datos del Encuentro")
    st.info("Sube el informe generado por tu simulador y la captura de las estadísticas finales.")
    
    col1, col2 = st.columns(2)
    with col1:
        pdf_input = st.file_uploader("📂 Informe PDF (Fase 2)", type="pdf")
    with col2:
        img_input = st.file_uploader("📸 Estadísticas Reales", type=["jpg", "png", "jpeg"])
    
    if st.button("▶ EJECUTAR ANÁLISIS INTEGRAL"):
        if pdf_input and img_input:
            with st.status("🧠 Analizando archivos con Gemini AI...", expanded=True) as status:
                resultado = procesar_con_ia(pdf_input, img_input)
                
                # Extracción de datos JSON para Supabase
                json_match = re.search(r'\{.*\}', resultado, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        supabase.table("auditoria_apuestas").insert(data).execute()
                        status.update(label="✅ Auditoría completada y sincronizada", state="complete")
                        
                        st.success("¡Datos guardados en Supabase!")
                        st.markdown("### 📋 Reporte de Auditoría Táctica")
                        # Mostramos el reporte omitiendo el JSON crudo
                        st.markdown(re.sub(r'```json.*?```', '', resultado, flags=re.DOTALL))
                    except Exception as e:
                        st.error(f"Error al sincronizar con la base de datos: {e}")
                else:
                    st.error("La IA no devolvió un formato de datos válido.")
        else:
            st.warning("Se requieren ambos archivos para proceder con la auditoría.")

with tabs[1]:
    # Carga de datos históricos desde Supabase
    try:
        res = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(res.data)

        if not df.empty:
            # Procesamiento de datos para gráficas
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['exactitud_val'] = df['exactitud_sim'].str.replace('%', '').astype(float)
            
            # Indicadores Clave (KPIs)
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Auditorías", len(df))
            wins = len(df[df['estado'] == '🟢'])
            k2.metric("Win Rate %", f"{(wins/len(df)*100):.1f}%")
            k3.metric("Eficacia de Modelo", f"{df['exactitud_val'].mean():.1f}%")
            
            st.write("---")
            
            # Visualizaciones
            g1, g2 = st.columns(2)
            with g1:
                fig_pie = px.pie(df, names='estado', hole=0.5, title="Rendimiento Estratégico",
                                color='estado', color_discrete_map={'🟢':'#2ea043','🔴':'#da3633','⚪':'#8b949e'})
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                fig_line = px.line(df.sort_values('fecha'), x='fecha', y='exactitud_val', 
                                  title="Evolución de Precisión de Simulación", markers=True)
                fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_line, use_container_width=True)
                
            st.subheader("📋 Registro Histórico de Auditorías")
            st.dataframe(df[['fecha', 'partido', 'marcador_final', 'estado', 'exactitud_sim', 'analisis_tecnico']], 
                         use_container_width=True, hide_index=True)
        else:
            st.info("No se han encontrado registros. Realiza tu primera auditoría para ver las métricas.")
    except:
        st.error("Error al conectar con el servidor de datos.")

# Botón lateral de refresco
if st.sidebar.button("Refrescar Base de Datos ↻"):
    st.rerun()

st.sidebar.caption("Quant/Sharp v3.0 | Auditoría Inteligente")