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
    page_title="Quant/Sharp Auditor Pro v8.1",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PREMIUM (PALETA DEEP SPACE & ANIMACIONES) ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    
    /* Animación de Carga Ultra-Sofisticada */
    .loader-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 40px 0;
    }
    .pulse-ring {
        border: 4px solid #1f6feb;
        border-radius: 50%;
        height: 80px;
        width: 80px;
        position: absolute;
        animation: pulsate 2s ease-out infinite;
        opacity: 0;
    }
    @keyframes pulsate {
        0% { transform: scale(0.1, 0.1); opacity: 0; }
        50% { opacity: 1; }
        100% { transform: scale(1.2, 1.2); opacity: 0; }
    }
    
    .loading-status-text {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 300;
        letter-spacing: 2px;
        color: #58a6ff;
        margin-top: 100px;
        text-transform: uppercase;
        font-size: 0.9rem;
    }

    /* Tarjetas de Apuestas (Paleta Refinada) */
    .bet-card {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    .hit { 
        border-left: 6px solid #238636; 
        background: linear-gradient(90deg, rgba(35, 134, 54, 0.1) 0%, rgba(13, 17, 23, 0) 100%);
    }
    .miss { 
        border-left: 6px solid #f85149; 
        background: linear-gradient(90deg, rgba(248, 81, 73, 0.1) 0%, rgba(13, 17, 23, 0) 100%);
    }
    
    /* Tabla Comparativa Moderna */
    .comp-table { width: 100%; border-collapse: separate; border-spacing: 0 8px; }
    .comp-table th { color: #8b949e; font-weight: 400; padding: 12px; text-align: left; border-bottom: 1px solid #30363d; }
    .comp-table td { background: #161b22; padding: 15px; }
    .comp-table tr td:first-child { border-radius: 10px 0 0 10px; }
    .comp-table tr td:last-child { border-radius: 0 10px 10px 0; }
    
    /* Consola */
    .console-box {
        background: #010409;
        color: #7ee787;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #30363d;
        font-family: 'Courier New', monospace;
        height: 200px;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# COMPONENTES VISUALES
# =====================================================================

def render_accuracy_gauge(score, title="Precisión del Informe", key_id="0"):
    """Crea un gráfico de medidor sofisticado con Plotly con ID único"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': title, 'font': {'size': 16, 'color': "#8b949e"}},
        number = {'suffix': "%", 'font': {'size': 40, 'color': "#ffffff"}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#30363d"},
            'bar': {'color': "#58a6ff"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 1,
            'bordercolor': "#30363d",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(248, 81, 73, 0.2)'},
                {'range': [40, 75], 'color': 'rgba(210, 153, 34, 0.2)'},
                {'range': [75, 100], 'color': 'rgba(46, 160, 67, 0.2)'}
            ]
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(t=40, b=0, l=20, r=20))
    return fig

# =====================================================================
# BARRA LATERAL (CONFIGURACIÓN)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Centro de Comando")
    manual_key = st.text_input("🔑 Gemini API Key:", type="password")
    model_option = st.selectbox("Motor IA:", ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-flash-latest"])
    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")
    
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            if st.button("🧪 Probar Conexión"):
                genai.list_models()
                st.success("Enlace Estable")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.subheader("🧹 Mantenimiento")
    if st.button("🔴 Borrado Maestro (Base en Blanco)"):
        try:
            # Obtenemos IDs para borrar
            res = supabase.table("auditoria_apuestas").select("id").execute()
            ids = [r['id'] for r in res.data]
            for record_id in ids:
                supabase.table("auditoria_apuestas").delete().eq("id", record_id).execute()
            st.success("Base de datos reiniciada.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error al borrar: {e}")

    st.divider()
    st.caption("Quant/Sharp v8.1 | Deep Space UI")

# =====================================================================
# MOTOR DE IA CON CARGA INTERACTIVA
# =====================================================================

def auditar_partido(pdf, img, model_choice, status_placeholder):
    """Procesamiento con visualización de pasos interactiva"""
    try:
        model = genai.GenerativeModel(model_name=model_choice, generation_config={"response_mime_type": "application/json"})
        
        steps = [
            "Estableciendo túnel cuántico...",
            "Escaneando métricas visuales del partido...",
            "Ejecutando backtesting contra Fase 2...",
            "Finalizando reporte de precisión..."
        ]
        
        for i, step in enumerate(steps):
            status_placeholder.markdown(f"""
                <div class="loader-wrapper">
                    <div class="pulse-ring"></div>
                    <div class="loading-status-text">{step} (Fase {i+1}/4)</div>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(1.5)
            add_log(step, "info")

        prompt = """
        [ROLE] Auditor de IA Deportiva. 
        [TASK] Cruza el PDF (Simulación Fase 2) con la Realidad (Imagen). 
        Calcula accuracy_score (0-100).
        [JSON] { "partido": "string", "pronostico": "string", "marcador_final": "string", "estado": "🟢/🔴", "accuracy_score": int, "apuestas_detalle": [{"apuesta": "string", "hit": bool}], "comparativa_simulacion": [{"metrica": "string", "informe": "string", "real": "string", "acerto": bool}], "analisis_tecnico": "Markdown" }
        """
        partes = [prompt, {"mime_type": "application/pdf", "data": pdf.getvalue()}, {"mime_type": "image/png", "data": img.getvalue()}]
        response = model.generate_content(partes)
        add_log("Análisis completado satisfactoriamente.", "success")
        return response.text, None
    except Exception as e:
        return None, str(e)

# =====================================================================
# INTERFAZ PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

t1, t2, t3 = st.tabs(["📄 AUDITORÍA", "🛡️ APUESTA MAESTRA", "📊 PANEL DE CONTROL"])

with t1:
    st.info("Inicia el proceso de auditoría multimodal para validar la precisión de tus informes.")
    c1, c2 = st.columns(2)
    with c1: pdfs = st.file_uploader("Informes PDF", type="pdf", accept_multiple_files=True)
    with c2: imgs = st.file_uploader("Capturas Estadísticas", type=["jpg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR PROCESAMIENTO"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            for i in range(len(pdfs)):
                status_area = st.empty()
                res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option, status_area)
                status_area.empty()
                
                if not err:
                    try:
                        data = json.loads(res_raw)
                        row = {
                            "partido": data['partido'], "pronostico": data['pronostico'],
                            "marcador_final": data['marcador_final'], "estado": data['estado'],
                            "tipo": "Individual", "analisis_tecnico": json.dumps(data)
                        }
                        supabase.table("auditoria_apuestas").insert(row).execute()
                        st.success(f"Finalizado: {data['partido']}")
                    except Exception as e: st.error(f"Error de formato: {e}")
                else: st.error(err)
        else:
            st.warning("Pares de archivos incompletos.")

    st.divider()
    with st.expander("🛠️ Consola de Sistema", expanded=True):
        logs = "\n".join(st.session_state.debug_logs[::-1])
        st.markdown(f'<div class="console-box">{logs}</div>', unsafe_allow_html=True)

# --- TAB 3: DASHBOARD ---
with t3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        db_data = response.data
        if db_data:
            df = pd.DataFrame(db_data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            # Métricas
            m1, m2, m3 = st.columns(3)
            hits = len(df[df['estado'].str.contains('🟢')])
            m1.metric("Informes", len(df))
            m2.metric("Acierto", f"{(hits/len(df)*100):.1f}%")
            m3.metric("Riesgo", "🛡️ Controlado")
            
            st.divider()

            for index, row in df.iterrows():
                try:
                    full_json = json.loads(row['analisis_tecnico'])
                    with st.expander(f"{row['estado']} {row['partido']} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                        
                        ca, cb = st.columns([1, 1.5])
                        with ca:
                            score = full_json.get('accuracy_score', 0)
                            # Añadimos KEY única para evitar el error de Plotly IDs
                            st.plotly_chart(render_accuracy_gauge(score, key_id=str(row['id'])), use_container_width=True, key=f"plotly_{row['id']}")

                        with cb:
                            st.markdown("#### 🎫 Evaluación de Apuestas")
                            for b in full_json.get('apuestas_detalle', []):
                                cls = "hit" if b["hit"] else "miss"
                                icon = "✅" if b["hit"] else "❌"
                                st.markdown(f'<div class="bet-card {cls}"><strong>{icon}</strong> {b["apuesta"]}</div>', unsafe_allow_html=True)
                        
                        st.markdown("#### 📉 Simulación vs Realidad")
                        comp_html = """<table class="comp-table"><thead><tr><th>Métrica</th><th>Informe</th><th>Realidad</th><th>OK</th></tr></thead><tbody>"""
                        for m in full_json.get('comparativa_simulacion', []):
                            icon = "🟢" if m['acerto'] else "🔴"
                            comp_html += f"<tr><td>{m['metrica']}</td><td>{m['informe']}</td><td>{m['real']}</td><td>{icon}</td></tr>"
                        comp_html += "</tbody></table>"
                        st.markdown(comp_html, unsafe_allow_html=True)
                        
                        st.info(f"**Conclusión:** {full_json.get('analisis_tecnico', 'Análisis finalizado.')}")
                        
                        # Botón de eliminación corregido
                        if st.button(f"🗑️ Eliminar Registro #{row['id']}", key=f"btn_del_{row['id']}"):
                            supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                            st.rerun()
                except Exception as e:
                    st.error(f"Error en carga #{row['id']}: {e}")
        else:
            st.info("Base de datos vacía.")
    except Exception as e:
        st.error(f"Error de enlace: {e}")

st.sidebar.caption("Quant/Sharp v8.1 | Deep Space UI")
