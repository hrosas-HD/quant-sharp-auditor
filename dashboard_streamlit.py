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
    page_title="Quant/Sharp Auditor Pro v8.3",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PREMIUM (V8.3 - FIX CARGA) ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    
    /* Animación de Carga Mejorada */
    .scanning-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 30px;
        background: rgba(22, 27, 34, 0.7);
        border-radius: 15px;
        border: 1px solid #30363d;
        margin: 20px 0;
    }
    .scan-line {
        width: 100%;
        height: 3px;
        background: #58a6ff;
        box-shadow: 0 0 15px #58a6ff;
        position: relative;
        animation: scan 1.5s ease-in-out infinite;
    }
    @keyframes scan {
        0% { transform: translateY(0); opacity: 0.2; }
        50% { transform: translateY(50px); opacity: 1; }
        100% { transform: translateY(0); opacity: 0.2; }
    }
    
    .loading-step { font-family: 'Courier New', monospace; color: #7ee787; margin-top: 20px; font-size: 1rem; }
    .quota-wait { color: #f85149; font-weight: bold; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

    /* Tarjetas de Apuestas */
    .bet-card { background: #161b22; border-radius: 10px; padding: 12px; margin-bottom: 10px; border: 1px solid #30363d; }
    .hit { border-left: 5px solid #238636; }
    .miss { border-left: 5px solid #da3633; }
    
    .console-box {
        background: #010409; color: #7ee787; padding: 15px; border-radius: 8px; border: 1px solid #30363d;
        font-family: 'Courier New', monospace; height: 180px; overflow-y: auto; font-size: 0.85rem;
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
        title = {'text': "Precisión de Simulación", 'font': {'size': 14, 'color': "#8b949e"}},
        number = {'suffix': "%", 'font': {'size': 35, 'color': "#ffffff"}},
        gauge = {
            'axis': {'range': [0, 100], 'tickcolor': "#30363d"},
            'bar': {'color': "#58a6ff"},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(218, 54, 51, 0.2)'},
                {'range': [40, 75], 'color': 'rgba(210, 153, 34, 0.2)'},
                {'range': [75, 100], 'color': 'rgba(35, 134, 54, 0.2)'}
            ]
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=180, margin=dict(t=30, b=0, l=10, r=10))
    return fig

# =====================================================================
# BARRA LATERAL (CENTRO DE COMANDO)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Centro de Comando")
    manual_key = st.text_input("🔑 Gemini API Key:", type="password")
    model_option = st.selectbox("Motor IA:", ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-flash-latest"])
    
    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")
    
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            if st.button("🧪 Probar Conexión API"):
                genai.list_models()
                st.success("Enlace Estable ✅")
                add_log("API Key validada.", "success")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.subheader("🧹 Mantenimiento")
    if st.button("🔴 Borrado Maestro (Base en Blanco)"):
        try:
            supabase.table("auditoria_apuestas").delete().neq("id", 0).execute()
            st.success("Base de datos reiniciada.")
            add_log("Limpieza total realizada.", "warning")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error al limpiar: {e}")

    st.divider()
    st.caption("Quant/Sharp v8.3 | Reliability & Maintenance")

# =====================================================================
# MOTOR DE IA CON FEEDBACK DE ESPERA REAL
# =====================================================================

def update_status_ui(placeholder, step_num, text, is_waiting=False):
    wait_html = '<div class="quota-wait"><br>⏳ LÍMITE DE CUOTA: Esperando reinicio (60s)...</div>' if is_waiting else ""
    placeholder.markdown(f"""
        <div class="scanning-wrapper">
            <div class="scan-line"></div>
            <div class="loading-step">[{step_num}/4] {text}</div>
            {wait_html}
        </div>
    """, unsafe_allow_html=True)

def auditar_partido(pdf, img, model_choice, status_placeholder):
    try:
        model = genai.GenerativeModel(model_name=model_choice, generation_config={"response_mime_type": "application/json"})
        
        # Fases visuales iniciales
        update_status_ui(status_placeholder, 1, "Analizando estructura del PDF...")
        time.sleep(1.5)
        update_status_ui(status_placeholder, 2, "Procesando visión de imagen...")
        time.sleep(1.5)
        update_status_ui(status_placeholder, 3, "Iniciando motor de comparación...")

        prompt = """
        [ROLE] Auditor Deportivo IA. 
        [TASK] Cruza el PDF con la Imagen. Calcula accuracy_score (0-100).
        [JSON] { "partido": "string", "pronostico": "string", "marcador_final": "string", "estado": "🟢/🔴", "accuracy_score": int, "apuestas_detalle": [{"apuesta": "string", "hit": bool}], "comparativa_simulacion": [{"metrica": "string", "informe": "string", "real": "string", "acerto": bool}], "analisis_tecnico": "Markdown" }
        """
        partes = [prompt, {"mime_type": "application/pdf", "data": pdf.getvalue()}, {"mime_type": "image/png", "data": img.getvalue()}]
        
        # Manejo de reintentos con feedback visual
        max_retries = 3
        for retry in range(max_retries):
            try:
                update_status_ui(status_placeholder, 4, "Generando reporte final...")
                response = model.generate_content(partes)
                add_log("Respuesta de IA recibida.", "success")
                return response.text, None
            except Exception as e:
                if "429" in str(e) and retry < max_retries - 1:
                    update_status_ui(status_placeholder, 4, "Esperando por saturación de API...", is_waiting=True)
                    add_log("Cuota agotada. Pausa de 60s.", "warning")
                    time.sleep(60)
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
    st.info("Valida tus simulaciones matemáticas con visión artificial y backtesting automático.")
    c1, c2 = st.columns(2)
    with c1: pdfs = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    with c2: imgs = st.file_uploader("Subir Capturas", type=["jpg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR PROCESAMIENTO"):
        if not GEMINI_API_KEY:
            st.error("⚠️ Falta API Key.")
        elif pdfs and imgs and len(pdfs) == len(imgs):
            for i in range(len(pdfs)):
                status_area = st.empty()
                res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option, status_area)
                status_area.empty()
                
                if not err:
                    try:
                        data = json.loads(res_raw)
                        row = {
                            "partido": data.get('partido', 'Desconocido'), 
                            "pronostico": data.get('pronostico', 'N/A'),
                            "marcador_final": data.get('marcador_final', '?-?'), 
                            "estado": data.get('estado', '⚪'),
                            "tipo": "Individual", 
                            "analisis_tecnico": json.dumps(data)
                        }
                        supabase.table("auditoria_apuestas").insert(row).execute()
                        st.success(f"Auditado: {row['partido']}")
                    except Exception as e: st.error(f"Error JSON: {e}")
                else:
                    st.error(f"Error: {err}")
        else:
            st.warning("Carga pares iguales de archivos.")

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
            m1.metric("Informes Totales", len(df))
            m2.metric("Acierto Estrategia", f"{(hits/len(df)*100 if len(df)>0 else 0):.1f}%")
            m3.metric("Filtro IA", "🛡️ Activo")
            
            st.divider()

            valid_records = []
            broken_records = []

            # Separamos registros buenos de corruptos
            for _, row in df.iterrows():
                try:
                    if row['analisis_tecnico']:
                        json.loads(row['analisis_tecnico'])
                        valid_records.append(row)
                    else:
                        broken_records.append(row)
                except:
                    broken_records.append(row)

            # Mostramos los válidos
            for row in valid_records:
                full_json = json.loads(row['analisis_tecnico'])
                with st.expander(f"{row['estado']} {row['partido']} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                    ca, cb = st.columns([1, 1.5])
                    with ca:
                        st.plotly_chart(render_accuracy_gauge(full_json.get('accuracy_score', 0), row['id']), use_container_width=True, key=f"g_{row['id']}")
                    with cb:
                        st.markdown("#### 🎫 Evaluación de Apuestas")
                        for b in full_json.get('apuestas_detalle', []):
                            st.markdown(f'<div class="bet-card {"hit" if b["hit"] else "miss"}">{"✅" if b["hit"] else "❌"} {b["apuesta"]}</div>', unsafe_allow_html=True)
                    
                    st.markdown("#### 📉 Comparativa de Métricas")
                    comp_html = """<table style='width:100%; border-collapse:collapse;'><thead><tr style='border-bottom:1px solid #333;'><th style='text-align:left; padding:8px;'>Métrica</th><th style='padding:8px;'>Informe</th><th style='padding:8px;'>Real</th></tr></thead><tbody>"""
                    for m in full_json.get('comparativa_simulacion', []):
                        comp_html += f"<tr style='border-bottom:1px solid #222;'><td style='padding:8px;'>{m['metrica']}</td><td style='text-align:center;'>{m['informe']}</td><td style='text-align:center;'>{m['real']} {'🟢' if m['acerto'] else '🔴'}</td></tr>"
                    comp_html += "</tbody></table>"
                    st.markdown(comp_html, unsafe_allow_html=True)
                    
                    st.info(f"**Conclusión:** {full_json.get('analisis_tecnico', 'Finalizado.')}")
                    if st.button(f"🗑️ Eliminar Informe #{row['id']}", key=f"del_{row['id']}"):
                        supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                        st.rerun()

            # Sección especial para limpiar datos basura (lo que causa que veas 7 en el contador pero no en la UI)
            if broken_records:
                st.divider()
                with st.expander("⚠️ Mantenimiento: Registros con Errores"):
                    st.warning(f"Se encontraron {len(broken_records)} registros corruptos que afectan al contador.")
                    for br in broken_records:
                        col1, col2 = st.columns([3, 1])
                        col1.write(f"Registro ID #{br['id']} (Fecha: {br['fecha']})")
                        if col2.button("Eliminar Basura", key=f"br_{br['id']}"):
                            supabase.table("auditoria_apuestas").delete().eq("id", br['id']).execute()
                            st.rerun()
        else:
            st.info("Sin datos.")
    except Exception as e:
        st.error(f"Error de base de datos.")

st.sidebar.caption("Quant/Sharp v8.3 | Dashboard Optimizado")
