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
    page_title="Quant/Sharp Auditor Pro v8.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PERSONALIZADOS (MODERNIZADOS) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    
    /* Animación de Carga Sofisticada */
    .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }
    .loading-bar-wrapper {
        width: 100%;
        max-width: 400px;
        height: 10px;
        background: #161b22;
        border-radius: 20px;
        position: relative;
        overflow: hidden;
        border: 1px solid #30363d;
    }
    .loading-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #1f6feb, #58a6ff);
        width: 0%;
        transition: width 0.5s ease;
        box-shadow: 0 0 10px rgba(88, 166, 255, 0.5);
    }
    
    /* Tarjetas de Apuestas (Paleta de colores mejorada) */
    .bet-card {
        background-color: #161b22;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #30363d;
        transition: transform 0.2s;
    }
    .bet-card:hover { transform: translateY(-2px); }
    .hit { border-top: 4px solid #2ea043; background: linear-gradient(180deg, #161b22 0%, #1c3224 100%); }
    .miss { border-top: 4px solid #f85149; background: linear-gradient(180deg, #161b22 0%, #321c1c 100%); }
    
    /* Tabla Comparativa */
    .comp-table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #0d1117; border-radius: 8px; overflow: hidden; }
    .comp-table th { padding: 12px; color: #8b949e; text-align: left; background: #161b22; font-size: 0.8rem; }
    .comp-table td { padding: 12px; border-bottom: 1px solid #21262d; color: #c9d1d9; }
    
    /* Consola de logs */
    .console-box {
        background-color: #000;
        color: #0f0;
        font-family: 'Courier New', Courier, monospace;
        padding: 10px;
        border-radius: 5px;
        height: 150px;
        overflow-y: auto;
        font-size: 0.8rem;
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

def render_accuracy_gauge(score, title="Precisión del Informe"):
    """Crea un gráfico de medidor sofisticado con Plotly"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': title, 'font': {'size': 18, 'color': "#8b949e"}},
        number = {'suffix': "%", 'font': {'color': "#58a6ff"}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#30363d"},
            'bar': {'color': "#1f6feb"},
            'bgcolor': "#161b22",
            'borderwidth': 2,
            'bordercolor': "#30363d",
            'steps': [
                {'range': [0, 50], 'color': '#3e1c1c'},
                {'range': [50, 80], 'color': '#3e3e1c'},
                {'range': [80, 100], 'color': '#1c3e24'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(t=50, b=0, l=20, r=20))
    return fig

# =====================================================================
# BARRA LATERAL (CONFIGURACIÓN RESTAURADA)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Configuración Pro")
    manual_key = st.text_input("🔑 Gemini API Key:", type="password", help="Genera una clave en Google AI Studio.")
    model_option = st.selectbox("Motor IA:", ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-flash-latest"])
    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")
    
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            if st.button("🔍 Validar Clave"):
                genai.list_models()
                st.success("✅ Conexión Estable")
                add_log("Validación de API exitosa.", "success")
        except Exception as e:
            st.error(f"❌ Error API: {e}")

    if st.button("🗑️ Limpiar Historial UI"):
        st.session_state.debug_logs = []
        st.rerun()
    
    st.divider()
    st.caption("Quant/Sharp v8.0 | Precision Engine")

# =====================================================================
# MOTOR DE IA CON PASO A PASO
# =====================================================================

def call_gemini_with_steps(model_name, parts, container):
    """Ejecuta la IA informando cada paso al usuario"""
    try:
        model = genai.GenerativeModel(model_name=model_name, generation_config={"response_mime_type": "application/json"})
        
        container.write("Step 1/4: Estableciendo conexión segura...")
        add_log("Conectando con Google AI...", "info")
        time.sleep(1)
        
        container.write("Step 2/4: Analizando visión computacional de la imagen...")
        add_log("IA procesando imagen de estadísticas...", "info")
        time.sleep(1.5)
        
        container.write("Step 3/4: Realizando backtesting de Fase 2...")
        add_log("Cotejando informe vs realidad...", "info")
        
        response = model.generate_content(parts)
        
        container.write("Step 4/4: Generando reporte de auditoría...")
        add_log("Recibiendo JSON de resultados.", "success")
        
        return response.text, None
    except Exception as e:
        return None, str(e)

def auditar_partido(pdf, img, model_choice, container):
    prompt = """
    [ROL] Auditor de Modelos Predictivos Deportivos.
    [TAREA] Analiza si la imagen es deportiva. Si no, devuelve "partido": "ERROR".
    Si es válida, cruza la "Fase 2: Simulación" del PDF con la realidad de la Imagen.
    
    [CALCULO DE SCORE]
    Calcula un "accuracy_score" (0-100) basado en cuántas apuestas se acertaron Y cuántos rangos de la Fase 2 (Goles, Corners, Tarjetas, Ambos Marcan) coinciden con la realidad.
    
    [ESTRUCTURA JSON]
    {
      "partido": "Nombre",
      "pronostico": "Resumen",
      "marcador_final": "X-X",
      "estado": "🟢/🔴",
      "accuracy_score": int,
      "apuestas_detalle": [{"apuesta": "Nombre", "hit": true}],
      "comparativa_simulacion": [{"metrica": "Nombre", "informe": "Rango", "real": "Valor", "acerto": true}],
      "metricas_visuales": {"xG": [0,0], "posesion": [0,0], "corners": [0,0]},
      "analisis_tecnico": "Markdown"
    }
    """
    partes = [prompt, {"mime_type": "application/pdf", "data": pdf.getvalue()}, {"mime_type": "image/png", "data": img.getvalue()}]
    return call_gemini_with_steps(model_choice, partes, container)

# =====================================================================
# INTERFAZ PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

t1, t2, t3 = st.tabs(["📄 AUDITORÍA", "🛡️ APUESTA MAESTRA", "📊 PANEL DE CONTROL"])

with t1:
    st.info("Sube tus informes y capturas para iniciar el flujo de validación inteligente.")
    c1, c2 = st.columns(2)
    with c1: pdfs = st.file_uploader("PDFs de Informe", type="pdf", accept_multiple_files=True)
    with c2: imgs = st.file_uploader("Capturas Estadísticas", type=["jpg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR PROCESAMIENTO INTELIGENTE"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            for i in range(len(pdfs)):
                # Contenedor de progreso animado
                p_box = st.container()
                with p_box:
                    st.subheader(f"Analizando: {pdfs[i].name}")
                    status_text = st.empty()
                    progress_bar = st.empty()
                    
                    # Simulación de barra de carga animada (Imagen 2 concept)
                    for percent in range(0, 101, 10):
                        progress_bar.markdown(f"""
                            <div class="loading-bar-wrapper">
                                <div class="loading-bar-fill" style="width: {percent}%;"></div>
                            </div>
                        """, unsafe_allow_html=True)
                        time.sleep(0.1)

                    res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option, status_text)
                    
                    if not err:
                        try:
                            data = json.loads(res_raw)
                            if data.get('partido') != "ERROR":
                                row = {
                                    "partido": data['partido'], "pronostico": data['pronostico'],
                                    "marcador_final": data['marcador_final'], "estado": data['estado'],
                                    "tipo": "Individual", "analisis_tecnico": json.dumps(data)
                                }
                                supabase.table("auditoria_apuestas").insert(row).execute()
                                st.success(f"Partido Auditado: {data['partido']}")
                                add_log(f"Guardado exitoso: {data['partido']}", "success")
                            else:
                                st.error("Imagen no válida detectada.")
                                add_log(f"Fallo de validación en {imgs[i].name}", "error")
                        except Exception as e: st.error(f"Error procesando JSON: {e}")
                    else: st.error(err)
                    time.sleep(2)
        else:
            st.warning("Debes subir pares iguales de archivos.")

    st.divider()
    with st.expander("🛠️ Consola de Registros Técnicos", expanded=True):
        if st.session_state.debug_logs:
            logs = "\n".join(st.session_state.debug_logs[::-1])
            st.markdown(f'<div class="console-box">{logs}</div>', unsafe_allow_html=True)
        else:
            st.write("Esperando acciones...")

# --- TAB 3: DASHBOARD (TOTALMENTE RENOVADO) ---
with t3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            k1, k2, k3 = st.columns(3)
            hits = len(df[df['estado'].str.contains('🟢')])
            k1.metric("Informes Auditados", len(df))
            k2.metric("% Éxito Estrategia", f"{(hits/len(df)*100):.1f}%")
            k3.metric("Protección", "🛡️ Nivel Alto")
            
            st.divider()

            for index, row in df.iterrows():
                try:
                    full_data = json.loads(row['analisis_tecnico'])
                    with st.expander(f"{row['estado']} {row['partido']} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                        
                        col_acc, col_bets = st.columns([1, 1.5])
                        
                        with col_acc:
                            # 4. MEDIDOR DE ACIERTO DINÁMICO
                            score = full_data.get('accuracy_score', 0)
                            st.plotly_chart(render_accuracy_gauge(score), use_container_width=True)

                        with col_bets:
                            # 1. EVALUACIÓN DE APUESTAS (NUEVA PALETA)
                            st.markdown("#### 🎫 Estatus de Apuestas")
                            for b in full_data.get('apuestas_detalle', []):
                                b_cls = "hit" if b["hit"] else "miss"
                                b_icon = "✅" if b["hit"] else "❌"
                                st.markdown(f'<div class="bet-card {b_cls}"><strong>{b_icon}</strong> {b["apuesta"]}</div>', unsafe_allow_html=True)
                        
                        # 2. COMPARATIVA TÉCNICA
                        st.markdown("#### 📊 Simulación vs Realidad")
                        table_html = """<table class="comp-table"><thead><tr><th>Métrica</th><th>Informe</th><th>Realidad</th><th>Estado</th></tr></thead><tbody>"""
                        for m in full_data.get('comparativa_simulacion', []):
                            icon = "🟢" if m['acerto'] else "🔴"
                            table_html += f"<tr><td>{m['metrica']}</td><td>{m['informe']}</td><td>{m['real']}</td><td>{icon}</td></tr>"
                        table_html += "</tbody></table>"
                        st.markdown(table_html, unsafe_allow_html=True)
                        
                        st.info(f"**Conclusión:** {full_data.get('analisis_tecnico', 'Proceso finalizado.')}")
                        
                        # 5. BOTÓN DE ELIMINACIÓN
                        if st.button(f"🗑️ Eliminar Informe #{row['id']}", key=f"del_{row['id']}"):
                            supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                            st.warning("Registro eliminado de la base de datos.")
                            time.sleep(1)
                            st.rerun()

                except Exception as e: st.error(f"Error cargando detalle: {e}")
        else:
            st.info("Sin registros en el historial.")
    except Exception as e:
        st.error(f"Fallo de conexión con Base de Datos.")

st.sidebar.caption("Quant/Sharp v8.0 | High Fidelity Mode")
