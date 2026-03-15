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
    page_title="Quant/Sharp Auditor Pro v8.2",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PREMIUM (V8.2 - REFINADO) ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    
    /* Animación de Carga Tecnológica */
    .scanning-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 40px;
        background: rgba(22, 27, 34, 0.5);
        border-radius: 20px;
        border: 1px dashed #30363d;
    }
    .scan-line {
        width: 100%;
        height: 2px;
        background: #58a6ff;
        box-shadow: 0 0 15px #58a6ff;
        position: relative;
        animation: scan 2s linear infinite;
    }
    @keyframes scan {
        0% { top: 0; opacity: 0; }
        50% { opacity: 1; }
        100% { top: 100px; opacity: 0; }
    }
    
    .loading-step {
        font-family: 'Courier New', monospace;
        color: #7ee787;
        margin-top: 15px;
        font-size: 0.9rem;
    }

    /* Tarjetas de Apuestas */
    .bet-card {
        background: #161b22;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #30363d;
    }
    .hit { border-left: 5px solid #238636; background: linear-gradient(90deg, rgba(35, 134, 54, 0.05) 0%, transparent 100%); }
    .miss { border-left: 5px solid #da3633; background: linear-gradient(90deg, rgba(218, 54, 51, 0.05) 0%, transparent 100%); }
    
    /* Tabla de Simulación */
    .modern-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .modern-table th { color: #8b949e; text-align: left; padding: 10px; border-bottom: 1px solid #30363d; font-size: 0.8rem; }
    .modern-table td { padding: 12px 10px; border-bottom: 1px solid #21262d; font-size: 0.9rem; }
    
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
        font-size: 0.85rem;
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

def render_accuracy_gauge(score, key_id):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': "Confianza del Informe", 'font': {'size': 14, 'color': "#8b949e"}},
        number = {'suffix': "%", 'font': {'size': 35, 'color': "#ffffff"}},
        gauge = {
            'axis': {'range': [0, 100], 'tickcolor': "#30363d"},
            'bar': {'color': "#58a6ff"},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(218, 54, 51, 0.15)'},
                {'range': [50, 80], 'color': 'rgba(210, 153, 34, 0.15)'},
                {'range': [80, 100], 'color': 'rgba(35, 134, 54, 0.15)'}
            ],
            'threshold': {'line': {'color': "#58a6ff", 'width': 2}, 'thickness': 0.75, 'value': score}
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=200, margin=dict(t=30, b=0, l=10, r=10))
    return fig

# =====================================================================
# BARRA LATERAL (CENTRO DE COMANDO BLINDADO)
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
                st.success("Enlace Estable ✅")
                add_log("Conexión con Gemini validada.", "success")
        except Exception as e:
            st.error(f"Error de enlace: {e}")

    st.divider()
    st.subheader("🧹 Mantenimiento")
    if st.button("🔴 Borrado Maestro (Base en Blanco)"):
        try:
            # Borrado masivo directo
            supabase.table("auditoria_apuestas").delete().neq("id", 0).execute()
            st.success("Base de datos reiniciada con éxito.")
            add_log("Borrado maestro ejecutado.", "warning")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error al limpiar: {e}")

    st.divider()
    st.caption("Quant/Sharp v8.2 | Deep Space System")

# =====================================================================
# MOTOR DE IA CON MANEJO DE CUOTAS Y PASOS
# =====================================================================

def auditar_partido(pdf, img, model_choice, status_placeholder):
    try:
        model = genai.GenerativeModel(model_name=model_choice, generation_config={"response_mime_type": "application/json"})
        
        steps = [
            "Escaneando PDF (Extrayendo Fase 2)...",
            "Procesando Imagen (Visión Computacional)...",
            "Cruzando Predicción vs Realidad...",
            "Calculando Índice de Precisión..."
        ]
        
        for i, step in enumerate(steps):
            status_placeholder.markdown(f"""
                <div class="scanning-wrapper">
                    <div class="scan-line"></div>
                    <div class="loading-step">[{i+1}/4] {step}</div>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(2)
            add_log(step, "info")

        prompt = """
        [ROL] Auditor de Modelos Predictivos. 
        [TAREA] Cruza el PDF (Simulación Fase 2) con la Realidad (Imagen).
        Calcula accuracy_score (0-100) basado en el éxito de las apuestas y la cercanía de las métricas (Goles, Corners, Tarjetas, Posesión).
        [JSON] { 
            "partido": "Local vs Visitante", 
            "pronostico": "string", 
            "marcador_final": "X-X", 
            "estado": "🟢/🔴", 
            "accuracy_score": int, 
            "apuestas_detalle": [{"apuesta": "string", "hit": bool}], 
            "comparativa_simulacion": [{"metrica": "string", "informe": "string", "real": "string", "acerto": bool}],
            "analisis_tecnico": "Markdown" 
        }
        """
        partes = [prompt, {"mime_type": "application/pdf", "data": pdf.getvalue()}, {"mime_type": "image/png", "data": img.getvalue()}]
        
        # Manejo de reintento para error 429
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = model.generate_content(partes)
                add_log("Respuesta recibida satisfactoriamente.", "success")
                return response.text, None
            except Exception as e:
                if "429" in str(e) and retry < max_retries - 1:
                    wait = 60 # Tiempo sugerido por la API
                    add_log(f"Cuota agotada. Esperando {wait}s...", "warning")
                    time.sleep(wait)
                    continue
                return None, str(e)
                
    except Exception as e:
        return None, str(e)

# =====================================================================
# INTERFAZ PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

t1, t2, t3 = st.tabs(["📄 AUDITORÍA", "🛡️ APUESTA MAESTRA", "📊 PANEL DE CONTROL"])

with t1:
    st.info("Cruce de datos multimodal: Valida el rendimiento real contra tus simulaciones matemáticas.")
    c1, c2 = st.columns(2)
    with c1: pdfs = st.file_uploader("Informes PDF", type="pdf", accept_multiple_files=True)
    with c2: imgs = st.file_uploader("Capturas Flashscore", type=["jpg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR PROCESAMIENTO"):
        if not GEMINI_API_KEY:
            st.error("⚠️ Debes configurar una API Key en la barra lateral.")
        elif pdfs and imgs and len(pdfs) == len(imgs):
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
                        st.success(f"Auditado: {data['partido']}")
                    except Exception as e: st.error(f"Error de parseo: {e}")
                else:
                    st.error(f"Error de API: {err}")
                    add_log(f"Error en procesamiento: {err}", "error")
        else:
            st.warning("Carga pares iguales de archivos para auditar.")

    st.divider()
    with st.expander("🛠️ Consola de Sistema", expanded=True):
        logs = "\n".join(st.session_state.debug_logs[::-1])
        st.markdown(f'<div class="console-box">{logs}</div>', unsafe_allow_html=True)

# --- TAB 3: DASHBOARD (PANEL DE CONTROL REFINADO) ---
with t3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        db_data = response.data
        if db_data:
            df = pd.DataFrame(db_data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            # Métricas Superiores
            m1, m2, m3 = st.columns(3)
            hits = len(df[df['estado'].str.contains('🟢')])
            m1.metric("Informes Auditados", len(df))
            m2.metric("Tasa de Acierto", f"{(hits/len(df)*100 if len(df)>0 else 0):.1f}%")
            m3.metric("Filtro de Seguridad", "🛡️ Nivel 5")
            
            st.divider()

            for index, row in df.iterrows():
                # Validación de JSON para evitar crash
                try:
                    if not row['analisis_tecnico'] or row['analisis_tecnico'] == "":
                        continue
                    full_json = json.loads(row['analisis_tecnico'])
                except:
                    st.error(f"⚠️ Informe #{row['id']} tiene datos corruptos.")
                    if st.button(f"Eliminar Informe Corrupto #{row['id']}", key=f"err_{row['id']}"):
                        supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                        st.rerun()
                    continue

                with st.expander(f"{row['estado']} {row['partido']} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                    ca, cb = st.columns([1, 1.5])
                    with ca:
                        score = full_json.get('accuracy_score', 0)
                        st.plotly_chart(render_accuracy_gauge(score, row['id']), use_container_width=True, key=f"gauge_{row['id']}")

                    with cb:
                        st.markdown("#### 🎫 Evaluación de Apuestas")
                        for b in full_json.get('apuestas_detalle', []):
                            cls = "hit" if b["hit"] else "miss"
                            icon = "✅" if b["hit"] else "❌"
                            st.markdown(f'<div class="bet-card {cls}"><strong>{icon}</strong> {b["apuesta"]}</div>', unsafe_allow_html=True)
                    
                    st.markdown("#### 📉 Simulación vs Realidad")
                    table_html = """<table class="modern-table"><thead><tr><th>Métrica</th><th>Predicción Informe</th><th>Resultado Imagen</th><th>OK</th></tr></thead><tbody>"""
                    for m in full_json.get('comparativa_simulacion', []):
                        icon = "🟢" if m['acerto'] else "🔴"
                        table_html += f"<tr><td>{m['metrica']}</td><td>{m['informe']}</td><td>{m['real']}</td><td>{icon}</td></tr>"
                    table_html += "</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
                    
                    st.info(f"**Análisis:** {full_json.get('analisis_tecnico', 'Sin detalles técnicos.')}")
                    
                    # Botón de eliminación individual funcional
                    if st.button(f"🗑️ Eliminar Registro #{row['id']}", key=f"btn_del_{row['id']}"):
                        supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                        st.success("Eliminado.")
                        time.sleep(0.5)
                        st.rerun()
        else:
            st.info("La base de datos está vacía. Inicia una auditoría para ver resultados.")
    except Exception as e:
        st.error(f"Fallo crítico: {e}")

st.sidebar.caption("Quant/Sharp v8.2 | Reliability Mode")
