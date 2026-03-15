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

# --- CONEXIÓN A APIS ---
# Plan A: Busca en st.secrets (Seguro). Plan B: Usa tus variables directamente (Para pruebas locales).
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://tnxhmhoczcbfmhieaxgt.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_4SX3y_184dNOObMxbRTIYA_3qSbfYUt")

supabase = None
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error inicializando Supabase: {e}")

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
                genai.list_models()
                st.success("Enlace Estable ✅")
                add_log(f"Clave validada para {model_option}", "success")
        except Exception as e:
            st.error(f"Error de clave Gemini: {e}")

    st.divider()
    if st.button("🔴 Borrado Maestro"):
        if supabase:
            try:
                supabase.table("auditoria_apuestas").delete().neq("id", 0).execute()
                st.success("Base limpia.")
                time.sleep(1) # Pequeña pausa para que se vea el mensaje
                st.rerun()
            except Exception as e:
                st.error(f"Error al borrar DB: {e}")
        else:
            st.error("No hay conexión a la base de datos.")

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

        # PROMPT ESTANDARIZADO Y ROBUSTO
        prompt = """
        Eres un auditor estadístico experto de apuestas deportivas. Tu tarea es cruzar los pronósticos y simulaciones de un informe técnico (PDF) con la realidad de un partido (Imagen de Flashscore).

        REGLAS MATEMÁTICAS DE CRUCE OBLIGATORIAS:
        1. Lee la imagen con atención para extraer: Marcador final, Patadas de esquina (córners), Tarjetas amarillas, Posesión de balón y xG (Metas Esperadas).
        2. Para evaluar apuestas en "apuestas_detalle", usa la lógica matemática, no intuición:
           - Si la apuesta es "Doble Oportunidad 1X": hit=true SOLO SI el equipo local ganó o hubo empate.
           - Si la apuesta es "Doble Oportunidad X2": hit=true SOLO SI el equipo visitante ganó o hubo empate.
           - Si la apuesta es "Menos de 2.5 Goles": suma los goles de la imagen. hit=true SOLO SI es 0, 1 o 2.
           - Si la apuesta es "Ambos Equipos Marcan - No": hit=true SOLO SI el marcador de la imagen tiene al menos un '0'.
           - Si la apuesta es sobre Córners (ej. +8.5 córners): suma los córners de la imagen y evalúa.
           - Si la apuesta es sobre Tarjetas: suma las tarjetas de la imagen y evalúa.
        3. El campo "accuracy_score" (0-100) debe ser matemático: (Apuestas hit=true / Total de apuestas evaluadas) * 100.
        4. En "comparativa_simulacion", cruza métricas de la 'Fase 2' del PDF frente a la imagen. Ejemplo:
           - metrica: "Posesión de balón" | informe: "Kocaelispor monopolizará (aprox 60-70%)" | real: "Eyüpspor 68% - Kocaelispor 32%" | acerto: false.
           - metrica: "Patadas de esquina" | informe: "9-11 totales" | real: "6 totales (3-3)" | acerto: false.

        Devuelve JSON ESTRICTAMENTE con esta estructura (sin bloques markdown fuera del JSON):
        {
          "partido": "Nombre Equipo A vs Nombre Equipo B",
          "pronostico": "Resumen general sugerido en el PDF",
          "marcador_final": "Marcador extraído de la imagen (ej. 0-1)",
          "estado": "🟢 (Si accuracy_score >= 50) o 🔴 (Si accuracy_score < 50)",
          "accuracy_score": int,
          "apuestas_detalle": [
            {"apuesta": "Nombre de la apuesta exacta del PDF (ej. Menos de 2.5 Goles)", "hit": true o false}
          ],
          "comparativa_simulacion": [
            {"metrica": "Ej. Córners, Posesión, Tarjetas", "informe": "Lo que predecía la fase 2 del PDF", "real": "El dato exacto extraído de la imagen", "acerto": true o false}
          ],
          "analisis_tecnico": "Breve explicación de por qué ganaron o perdieron las apuestas basado en los datos duros cruzados."
        }
        """
        
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
                        # Prevenir errores de bloque markdown ```json
                        clean_json = res_raw.strip().strip('```json').strip('```')
                        raw_data = json.loads(clean_json)
                        data = raw_data[0] if isinstance(raw_data, list) else raw_data
                        
                        row = {
                            "partido": data.get('partido', 'Desconocido'),
                            "pronostico": data.get('pronostico', 'N/A'),
                            "marcador_final": data.get('marcador_final', '?-?'),
                            "estado": data.get('estado', '⚪'),
                            "tipo": "Individual",
                            "analisis_tecnico": json.dumps(data)
                        }
                        if supabase:
                            supabase.table("auditoria_apuestas").insert(row).execute()
                            st.success(f"Auditado y guardado con éxito: {row['partido']}")
                        else:
                            st.warning(f"Auditado, pero NO guardado (Sin DB): {row['partido']}")
                            st.json(row) # Mostramos el resultado si no hay BD
                            
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

# --- TAB 2: APUESTA MAESTRA ---
with t2:
    st.subheader("🛡️ Gestión de Apuestas Maestras")
    st.info("Módulo en desarrollo. Aquí puedes agregar lógica para combinar métricas cruzadas.")

# --- TAB 3: DASHBOARD ---
with t3:
    col_ref, empty_col = st.columns([1, 4])
    with col_ref:
        if st.button("🔄 Refrescar Datos"):
            st.rerun()
        
    try:
        if supabase:
            res = supabase.table("auditoria_apuestas").select("*").order("fecha", desc=True).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df['fecha'] = pd.to_datetime(df['fecha'])
                
                m1, m2, m3 = st.columns(3)
                hits = len(df[df['estado'].astype(str).str.contains('🟢', na=False)])
                m1.metric("Informes Auditados", len(df))
                m2.metric("Tasa de Acierto Global", f"{(hits/len(df)*100 if len(df)>0 else 0):.1f}%")
                m3.metric("Riesgo", "🛡️ Activo")
                
                st.divider()

                for _, row in df.iterrows():
                    try:
                        if not row['analisis_tecnico']: continue
                        full_json = json.loads(row['analisis_tecnico'])
                        data = full_json[0] if isinstance(full_json, list) else full_json
                        
                        with st.expander(f"{row.get('estado', '⚪')} {row.get('partido', 'Unknown')} | {row.get('marcador_final', '')} | {row['fecha'].strftime('%d/%m %H:%M')}"):
                            ca, cb = st.columns([1, 2])
                            with ca:
                                st.write(f"**Confianza Auditoría:** {data.get('accuracy_score', 0)}%")
                                st.write("---")
                                if st.button("🗑️ Borrar", key=f"del_{row['id']}"):
                                    supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                                    st.rerun()
                            with cb:
                                st.markdown("##### 🎯 Evaluación de Apuestas (Fase 3)")
                                for b in data.get('apuestas_detalle', []):
                                    is_hit = b.get("hit", False)
                                    txt_apuesta = b.get("apuesta", "Detalle desconocido")
                                    st.markdown(f'{"✅" if is_hit else "❌"} **{txt_apuesta}**')
                                
                                st.markdown("---")
                                st.markdown("##### 📊 Comparativa de Simulaciones (Fase 2)")
                                for sim in data.get('comparativa_simulacion', []):
                                    st.markdown(f"**{sim.get('metrica', 'Métrica')}**: Informe preveía _{sim.get('informe', 'N/A')}_ vs Realidad: **{sim.get('real', 'N/A')}** {'✅' if sim.get('acerto') else '❌'}")
                                    
                                if "analisis_tecnico" in data:
                                    st.markdown("---")
                                    st.markdown(f"**Resumen Técnico:** {data['analisis_tecnico']}")
                    except Exception as e:
                        st.error(f"Fila ID {row.get('id')} corrupta.")
                        if st.button(f"Limpiar Registro #{row.get('id')}", key=f"fix_{row.get('id')}"):
                            supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                            st.rerun()
            else: 
                st.info("Base de datos vacía. Realiza tu primera auditoría.")
        else:
            st.error("No se pudo conectar a Supabase. Revisa las credenciales.")
    except Exception as e: 
        st.error(f"Error de conexión con Supabase o procesando DB: {e}")
