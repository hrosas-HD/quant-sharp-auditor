import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import google.generativeai as genai
import re
import json
import time
import random

# =====================================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Quant/Sharp Auditor Pro v7.8",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE LOGS PARA CONSOLA ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PERSONALIZADOS (FLASHCORE STYLE + PREMIUM) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stat-bar-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 15px;
        padding: 5px 0;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #8b949e;
        text-align: center;
        flex: 1;
        font-weight: bold;
        text-transform: uppercase;
    }
    .stat-value {
        width: 40px;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .bar-bg {
        flex: 3;
        height: 12px;
        background-color: #30363d;
        border-radius: 6px;
        margin: 0 15px;
        position: relative;
        overflow: hidden;
    }
    .bar-home {
        height: 100%;
        background-color: #e91e63; /* Rosa/Rojo Flashscore */
        position: absolute;
        right: 50%;
        border-radius: 6px 0 0 6px;
    }
    .bar-away {
        height: 100%;
        background-color: #ffffff; /* Blanco Flashscore */
        position: absolute;
        left: 50%;
        border-radius: 0 6px 6px 0;
    }
    .bet-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 8px;
    }
    .hit { border-left: 5px solid #238636; }
    .miss { border-left: 5px solid #da3633; }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .loading-text {
        font-size: 1.1rem;
        color: #58a6ff;
        font-weight: bold;
        animation: pulse 1.5s infinite;
        text-align: center;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
SUPABASE_URL = "https://tnxhmhoczcbfmhieaxgt.supabase.co"
SUPABASE_KEY = "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt"

# =====================================================================
# BARRA LATERAL (CONTROL TOTAL RESTAURADO)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Auditor Pro v7.8")
    
    # 1. Entrada Manual de Clave
    manual_key = st.text_input("🔑 Gemini API Key (Manual):", type="password", help="Pega tu nueva clave de AI Studio aquí.")
    
    # 2. Selector de Modelo
    model_option = st.selectbox(
        "Motor de Inteligencia:",
        ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-flash-latest"],
        index=0
    )
    
    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")
    
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            if st.button("🔍 Probar Validez de Clave"):
                models = [m.name for m in genai.list_models()]
                st.success("✅ Clave Activa y Funcional")
                add_log("Prueba de conexión exitosa.", "success")
        except Exception as e:
            st.error(f"❌ Error de Clave: {e}")
            add_log(f"Fallo en prueba de conexión: {str(e)}", "error")
    
    if st.button("🗑️ Limpiar Consola Técnica"):
        st.session_state.debug_logs = []
        st.rerun()

    st.divider()
    st.caption("Quant/Sharp v7.8 | Consola e IA Restauradas")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================================
# COMPONENTES VISUALES
# =====================================================================
def render_stat_bar(label, val_home, val_away):
    """Genera una barra comparativa estilo Flashscore"""
    total = float(val_home) + float(val_away) if (float(val_home) + float(val_away)) > 0 else 1.0
    p_home = (float(val_home) / total) * 50
    p_away = (float(val_away) / total) * 50
    
    st.markdown(f"""
        <div class="stat-bar-container">
            <div class="stat-value" style="text-align: right;">{val_home}</div>
            <div class="bar-bg">
                <div class="bar-home" style="width: {p_home}%;"></div>
                <div class="bar-away" style="width: {p_away}%;"></div>
            </div>
            <div class="stat-value" style="text-align: left;">{val_away}</div>
        </div>
        <div style="text-align: center; margin-top: -15px; margin-bottom: 20px;">
            <span class="stat-label">{label}</span>
        </div>
    """, unsafe_allow_html=True)

# =====================================================================
# MOTOR DE IA MEJORADO CON RETRY Y VALIDACIÓN
# =====================================================================
def call_gemini_with_retry(model_name, parts, max_retries=5):
    try:
        model = genai.GenerativeModel(model_name=model_name, generation_config={"response_mime_type": "application/json"})
        for i in range(max_retries):
            try:
                add_log(f"Intento {i+1} con {model_name}...", "info")
                response = model.generate_content(parts)
                return response.text, None
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    delay_match = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', err_str)
                    wait = int(delay_match.group(1)) + 2 if delay_match else (i + 1) * 15
                    add_log(f"Cuota agotada. Pausa de {wait}s...", "warning")
                    time.sleep(wait)
                    continue
                return None, err_str
        return None, "Límite excedido tras reintentos."
    except Exception as e: return None, str(e)

def auditar_partido(pdf, img, model_choice):
    prompt = """
    [ROL] Auditor Senior de Datos Deportivos Pro.
    
    [PASO 1: VALIDACIÓN]
    Analiza la IMAGEN. ¿Es una captura de estadísticas reales de fútbol? Si no, devuelve "partido": "ERROR_IMAGEN_INVALIDA".
    
    [PASO 2: EXTRACCIÓN]
    - Deconstruye las 3 APUESTAS principales del PDF.
    - Extrae la SIMULACIÓN FASE 2.
    
    [PASO 3: AUDITORÍA]
    Compara las apuestas y la Fase 2 contra la realidad de la imagen.
    
    [ESTRUCTURA JSON]
    {
      "partido": "Local vs Visitante o ERROR_IMAGEN_INVALIDA",
      "pronostico": "Resumen",
      "marcador_final": "X-X",
      "estado": "🟢/🔴",
      "tipo": "Individual",
      "apuestas_detalle": [
          {"apuesta": "Nombre", "hit": true/false}
      ],
      "metricas_visuales": {
          "xG": [v1, v2], "posesion": [v1, v2], "disparos": [v1, v2], "corners": [v1, v2], "tarjetas": [v1, v2]
      },
      "analisis_tecnico": "Resumen del backtesting."
    }
    """
    partes = [prompt, {"mime_type": "application/pdf", "data": pdf.getvalue()}, {"mime_type": "image/png", "data": img.getvalue()}]
    return call_gemini_with_retry(model_choice, partes)

# =====================================================================
# INTERFAZ PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

t1, t2, t3 = st.tabs(["📄 AUDITORÍA", "🛡️ APUESTA MAESTRA", "📊 PANEL DE CONTROL"])

# --- TAB 1: AUDITORÍA ---
with t1:
    st.info("Procesamiento secuencial con guardián de validación de imágenes activo.")
    col_u1, col_u2 = st.columns(2)
    with col_u1: pdfs = st.file_uploader("Informes (PDF)", type="pdf", accept_multiple_files=True)
    with col_u2: imgs = st.file_uploader("Resultados (IMG)", type=["jpg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR AUDITORÍA"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            with st.status("🚀 Auditando lotes...", expanded=True) as status:
                for i in range(len(pdfs)):
                    msg = f"Analizando {pdfs[i].name}..."
                    st.markdown(f'<p class="loading-text">{msg}</p>', unsafe_allow_html=True)
                    res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option)
                    
                    if not err:
                        try:
                            data = json.loads(res_raw)
                            if data.get('partido') == "ERROR_IMAGEN_INVALIDA":
                                st.error(f"❌ Imagen inválida detectada en {imgs[i].name}")
                                add_log(f"Validación fallida: {imgs[i].name}", "error")
                            else:
                                row = {
                                    "partido": data['partido'], "pronostico": data['pronostico'],
                                    "marcador_final": data['marcador_final'], "estado": data['estado'],
                                    "tipo": "Individual", "analisis_tecnico": json.dumps(data)
                                }
                                supabase.table("auditoria_apuestas").insert(row).execute()
                                st.success(f"✅ Auditado: {data['partido']}")
                                add_log(f"Éxito: {data['partido']}", "success")
                        except Exception as e: st.error(f"Error JSON: {e}")
                    else: st.error(err); add_log(f"Fallo en {pdfs[i].name}: {err}", "error")
                    time.sleep(5)
                status.update(label="✅ Procesamiento completado", state="complete")

    st.divider()
    with st.expander("🛠️ Consola de Depuración Técnica", expanded=len(st.session_state.debug_logs) > 0):
        if st.session_state.debug_logs:
            log_content = "\n".join(st.session_state.debug_logs[::-1])
            st.text_area("Logs de sistema", value=log_content, height=250, disabled=True)
        else: st.write("Sin eventos.")

# --- TAB 2: APUESTA MAESTRA ---
with t2:
    st.subheader("Validación Final de la Guillotina")
    col_m1, col_m2 = st.columns([1, 1])
    with col_m1: m_text = st.text_area("Texto Prompt 2", height=250)
    with col_m2: m_img = st.file_uploader("Captura Maestro", type=["jpg", "png"], key="m_img")
    
    if st.button("▶ VALIDAR MAESTRA"):
        if m_text and m_img:
            with st.status("🔍 Verificando..."):
                prompt = f"Valida si la imagen es de fútbol. Si no, devuelve partido: 'ERROR'. Si sí, audita el texto: {m_text} y devuelve JSON con tipo: 'Maestra'."
                partes = [prompt, {"mime_type": "image/png", "data": m_img.getvalue()}]
                res_raw, err = call_gemini_with_retry(model_option, partes)
                if not err:
                    data = json.loads(res_raw)
                    if data.get('partido') != "ERROR":
                        row = {"partido": data.get('partido'), "pronostico": data.get('pronostico'), "estado": data.get('estado'), "tipo": "Maestra", "analisis_tecnico": json.dumps(data)}
                        supabase.table("auditoria_apuestas").insert(row).execute()
                        st.balloons(); st.success("✅ Maestra Guardada")
                    else: st.error("Imagen inválida.")

# --- TAB 3: DASHBOARD ---
with t3:
    try:
        response = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            filt = st.pills("Filtrar:", ["Todos", "Individuales", "Maestras"], default="Todos")
            df_v = df if filt == "Todos" else df[df['tipo'] == ('Individual' if filt == "Individuales" else 'Maestra')]
            
            k1, k2, k3 = st.columns(3)
            hits = len(df_v[df_v['estado'].str.contains('🟢')])
            k1.metric("Análisis", len(df_v))
            k2.metric("Acierto %", f"{(hits/len(df_v)*100 if len(df_v)>0 else 0):.1f}%")
            k3.metric("Estatus", "🛡️ Seguro" if hits > 0 else "⚖️ Estable")
            
            st.divider()

            for index, row in df_v.iterrows():
                try:
                    full_data = json.loads(row['analisis_tecnico'])
                    with st.expander(f"{row['estado']} {row['partido']} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                        # 🎫 APUESTAS
                        st.markdown("#### 🎫 Estatus de Apuestas")
                        b_cols = st.columns(3)
                        for i, bet in enumerate(full_data.get('apuestas_detalle', [])):
                            with b_cols[i % 3]:
                                st.markdown(f'<div class="bet-card {"hit" if bet["hit"] else "miss"}"><strong>{"✅" if bet["hit"] else "❌"} Apuesta {i+1}</strong><br><small>{bet["apuesta"]}</small></div>', unsafe_allow_html=True)
                        
                        # 📊 BARRAS TÉCNICAS
                        st.markdown("---")
                        st.markdown("#### 📊 Realidad del Partido")
                        m = full_data.get('metricas_visuales', {})
                        if m:
                            render_stat_bar("Metas Esperadas (xG)", m.get('xG',[0,0])[0], m.get('xG',[0,0])[1])
                            render_stat_bar("Posesión %", m.get('posesion',[0,0])[0], m.get('posesion',[0,0])[1])
                            render_stat_bar("Corners", m.get('corners',[0,0])[0], m.get('corners',[0,0])[1])
                        
                        st.info(f"**Conclusión:** {full_data.get('analisis_tecnico', 'Finalizado.')}")
                except: st.write(row['analisis_tecnico'])
        else: st.info("Sin registros.")
    except Exception as e: st.error(f"Error DB: {e}")

st.sidebar.caption("Quant/Sharp v7.8 | Centro de Control Unificado")
