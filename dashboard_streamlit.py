import streamlit as st
import pandas as pd
from supabase import create_client, Client
import google.generativeai as genai
import json
import time

# =====================================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Quant/Sharp Auditor Pro v8.7",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN ---
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []
if "exhausted_models" not in st.session_state:
    st.session_state.exhausted_models = []

def add_log(msg, type="info"):
    st.session_state.debug_logs.append(f"[{time.strftime('%H:%M:%S')}] [{type.upper()}] {msg}")

# --- ESTILOS CSS PREMIUM ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .scanning-wrapper {
        display: flex; flex-direction: column; align-items: center; padding: 30px;
        background: rgba(22, 27, 34, 0.8); border-radius: 15px; border: 1px solid #30363d; margin: 20px 0;
    }
    .scan-line {
        width: 100%; height: 3px; background: #58a6ff; box-shadow: 0 0 15px #58a6ff;
        position: relative; animation: scan 1.5s ease-in-out infinite;
    }
    @keyframes scan { 0% { transform: translateY(0); opacity: 0.2; } 50% { transform: translateY(40px); opacity: 1; } 100% { transform: translateY(0); opacity: 0.2; } }
    .loading-step { font-family: 'Courier New', monospace; color: #7ee787; margin-top: 20px; font-size: 1rem; }
    .bet-card { background: #161b22; border-radius: 10px; padding: 12px; margin-bottom: 10px; border: 1px solid #30363d; }
    .hit { border-left: 5px solid #238636; }
    .miss { border-left: 5px solid #da3633; }
    .console-box {
        background: #010409; color: #7ee787; padding: 15px; border-radius: 8px; border: 1px solid #30363d;
        font-family: 'Courier New', monospace; height: 180px; overflow-y: auto; font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS (SEGURA) ---
# Requiere configurar st.secrets (ej: secrets.toml)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "URL_POR_DEFECTO_SI_NO_EXISTE")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "KEY_POR_DEFECTO_SI_NO_EXISTE")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error inicializando Supabase: Verifica tus secrets. {e}")

# =====================================================================
# BARRA LATERAL (CENTRO DE COMANDO)
# =====================================================================
with st.sidebar:
    st.header("⚙️ Centro de Comando")
    manual_key = st.text_input("🔑 Gemini API Key:", type="password")
    
    model_options = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]
    display_opts = [f"{m} {' (⚠️ AGOTADO)' if m in st.session_state.exhausted_models else ''}" for m in model_options]
    model_selection = st.selectbox("Motor IA:", options=display_opts, index=0)
    model_option = model_selection.split(' ')[0]
    
    GEMINI_API_KEY = manual_key if manual_key else st.secrets.get("GEMINI_API_KEY", "")
    
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            if st.button("🧪 Probar Conexión"):
                genai.list_models() # Fuerza una llamada ligera a la API
                st.success("Enlace Estable ✅")
                add_log(f"Clave validada para {model_option}", "success")
        except Exception as e:
            st.error(f"Error de clave Gemini: {e}")

    st.divider()
    if st.button("🔴 Borrado Maestro"):
        try:
            supabase.table("auditoria_apuestas").delete().neq("id", 0).execute()
            st.success("Base limpia.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al borrar DB: {e}")

    st.caption("Quant/Sharp v8.7 | JSON Recovery")

# =====================================================================
# MOTOR DE IA CON ROBUSTEZ DE DATOS
# =====================================================================

def update_status_ui(placeholder, step_num, text, wait_secs=0):
    timer = f'<div style="color:#f85149">⏳ REINTENTO EN: {wait_secs}s</div>' if wait_secs > 0 else ""
    placeholder.markdown(f"""
        <div class="scanning-wrapper">
            <div class="scan-line"></div>
            <div class="loading-step">[{step_num}/4] {text}</div>
            {timer}
        </div>
    """, unsafe_allow_html=True)

def auditar_partido(pdf, img, model_choice, status_placeholder):
    try:
        model = genai.GenerativeModel(model_name=model_choice, generation_config={"response_mime_type": "application/json"})
        update_status_ui(status_placeholder, 1, "Leyendo PDF...")
        time.sleep(0.5)
        update_status_ui(status_placeholder, 2, "Procesando Imagen...")
        time.sleep(0.5)
        update_status_ui(status_placeholder, 3, "Cruzando métricas...")

        prompt = """
        Analiza PDF vs Imagen. Devuelve JSON estrictamente con esta estructura:
        { "partido": "string", "pronostico": "string", "marcador_final": "string", "estado": "🟢 o 🔴", "accuracy_score": int, 
          "apuestas_detalle": [{"apuesta": "string", "hit": true/false}], 
          "comparativa_simulacion": [{"metrica": "string", "informe": "string", "real": "string", "acerto": true/false}], "analisis_tecnico": "Markdown" }
        """
        
        # FIX: Mime type dinámico según la imagen subida (PNG/JPEG)
        img_mime_type = img.type if img.type else "image/png"
        
        partes = [
            prompt, 
            {"mime_type": "application/pdf", "data": pdf.getvalue()}, 
            {"mime_type": img_mime_type, "data": img.getvalue()}
        ]
        
        for retry in range(3):
            try:
                update_status_ui(status_placeholder, 4, "Finalizando inferencia...")
                response = model.generate_content(partes)
                return response.text, None
            except Exception as e:
                error_str = str(e)
                if "429" in error_str:
                    for r in range(60, 0, -1):
                        update_status_ui(status_placeholder, 4, "Cuota de API agotada, esperando...", wait_secs=r)
                        time.sleep(1)
                    continue
                return None, error_str
        return None, "Límite de intentos superado por error 429."
    except Exception as e: 
        return None, str(e)

# =====================================================================
# INTERFAZ PRINCIPAL
# =====================================================================
st.title("🎯 Quant/Sharp Auditor Pro")

t1, t2, t3 = st.tabs(["📄 AUDITORÍA", "🛡️ APUESTA MAESTRA", "📊 PANEL DE CONTROL"])

# --- TAB 1: AUDITORÍA ---
with t1:
    c1, c2 = st.columns(2)
    with c1: pdfs = st.file_uploader("PDFs", type="pdf", accept_multiple_files=True)
    with c2: imgs = st.file_uploader("Capturas", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            for i in range(len(pdfs)):
                status_area = st.empty()
                res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option, status_area)
                status_area.empty()
                
                if not err and res_raw:
                    try:
                        raw_data = json.loads(res_raw)
                        data = raw_data[0] if isinstance(raw_data, list) else raw_data
                        
                        row = {
                            "partido": data.get('partido', 'Desconocido'),
                            "pronostico": data.get('pronostico', 'N/A'),
                            "marcador_final": data.get('marcador_final', '?-?'),
                            "estado": data.get('estado', '⚪'),
                            "tipo": "Individual",
                            "analisis_tecnico": json.dumps(data)
                        }
                        supabase.table("auditoria_apuestas").insert(row).execute()
                        st.success(f"Auditado con éxito: {row['partido']}")
                    except json.JSONDecodeError:
                        st.error(f"Fallo al interpretar el JSON de la IA. Respuesta cruda: {res_raw}")
                    except Exception as e:
                        st.error(f"Error al guardar en BD: {e}")
                else: 
                    st.error(f"Error en inferencia: {err}")
        else: 
            st.warning("Asegúrate de cargar exactamente la misma cantidad de PDFs y Capturas para emparejarlos.")

    st.divider()
    with st.expander("🛠️ Consola de Depuración", expanded=False):
        logs = "\n".join(st.session_state.debug_logs[::-1])
        st.markdown(f'<div class="console-box">{logs if logs else "Sin registros."}</div>', unsafe_allow_html=True)

# --- TAB 2: APUESTA MAESTRA (Añadido) ---
with t2:
    st.subheader("🛡️ Gestión de Apuestas Maestras")
    st.info("Módulo en desarrollo. Aquí puedes agregar lógica para combinar métricas cruzadas.")

# --- TAB 3: DASHBOARD ---
with t3:
    if st.button("🔄 Refrescar Datos"):
        st.rerun()
        
    try:
        res = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            m1, m2, m3 = st.columns(3)
            # FIX: Convertimos a string por seguridad antes de hacer str.contains
            hits = len(df[df['estado'].astype(str).str.contains('🟢', na=False)])
            m1.metric("Informes Auditados", len(df))
            m2.metric("Tasa de Acierto", f"{(hits/len(df)*100 if len(df)>0 else 0):.1f}%")
            m3.metric("Riesgo", "🛡️ Activo")
            
            st.divider()

            for _, row in df.iterrows():
                try:
                    if not row['analisis_tecnico']: continue
                    full_json = json.loads(row['analisis_tecnico'])
                    data = full_json[0] if isinstance(full_json, list) else full_json
                    
                    with st.expander(f"{row.get('estado', '⚪')} {row.get('partido', 'Unknown')} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                        ca, cb = st.columns([1, 2])
                        with ca:
                            st.write(f"**Confianza IA:** {data.get('accuracy_score', 0)}%")
                            if st.button("🗑️ Borrar", key=f"del_{row['id']}"):
                                supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                                st.rerun()
                        with cb:
                            for b in data.get('apuestas_detalle', []):
                                # Usamos .get() para evitar KeyErrors si el JSON viene deformado
                                is_hit = b.get("hit", False)
                                txt_apuesta = b.get("apuesta", "Detalle desconocido")
                                st.markdown(f'{"✅" if is_hit else "❌"} {txt_apuesta}')
                except Exception as e:
                    st.error(f"Fila ID {row.get('id')} corrupta.")
                    if st.button(f"Limpiar Registro #{row.get('id')}", key=f"fix_{row.get('id')}"):
                        supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                        st.rerun()
        else: 
            st.info("Base de datos vacía. Realiza tu primera auditoría.")
    except Exception as e: 
        st.error(f"Error de conexión con Supabase o procesando DB: {e}")
