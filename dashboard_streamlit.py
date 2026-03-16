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

# --- ESTILOS CSS PREMIUM (ESTILO CYBER-QUANT / HACKER) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;700&family=Inter:wght@400;600;800&display=swap');

    /* =======================================================
       1. FONDOS GLOBALES Y TIPOGRAFÍA
       ======================================================= */
    .stApp, [data-testid="stAppViewContainer"], .main { 
        background-color: #050505 !important; 
        color: #e0e0e0 !important; 
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stSidebar"] { 
        background-color: #0a0a0a !important; 
        border-right: 1px solid #1f1f1f !important; 
    }
    h1, h2, h3, h4, h5, h6, p, span { 
        color: #ffffff !important; 
    }
    h1, h2, h3 {
        font-family: 'Fira Code', monospace !important;
    }
    hr { border-color: #1f1f1f !important; }

    /* =======================================================
       2. CORRECCIÓN DE ELEMENTOS NATIVOS DE STREAMLIT (ADIÓS BLANCOS)
       ======================================================= */
    
    /* Expanders (Acordeones de Auditoría) */
    [data-testid="stExpander"] {
        background-color: #0a0a0a !important;
        border: 1px solid #1f1f1f !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    [data-testid="stExpander"] details summary {
        background-color: #111111 !important;
        color: #00f0ff !important;
    }
    [data-testid="stExpander"] details summary:hover {
        background-color: #1a1a1a !important;
        color: #39ff14 !important;
    }
    [data-testid="stExpander"] div[role="button"] p {
        color: #00f0ff !important;
        font-family: 'Fira Code', monospace !important;
    }

    /* Subidor de Archivos (File Uploader) */
    [data-testid="stFileUploader"] > section {
        background-color: #0a0a0a !important;
        border: 1px dashed #1f1f1f !important;
        color: #8b949e !important;
    }
    [data-testid="stFileUploader"] > section:hover {
        border-color: #00f0ff !important;
        background-color: #111111 !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
        color: #8b949e !important;
    }

    /* Pestañas (Tabs) */
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        background-color: transparent !important;
        color: #8b949e !important;
        border-bottom-color: #1f1f1f !important;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        color: #00f0ff !important;
        background-color: #0a0a0a !important;
        border-bottom-color: #00f0ff !important;
    }

    /* Botones Generales y Cajas de Texto */
    .stButton button {
        background-color: #0a0a0a !important;
        color: #00f0ff !important;
        border: 1px solid #1f1f1f !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        border-color: #00f0ff !important;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.2) !important;
        color: #ffffff !important;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0a0a0a !important;
        color: #00f0ff !important;
        border: 1px solid #1f1f1f !important;
    }
    .stAlert {
        background-color: #0a0a0a !important;
        border: 1px solid #1f1f1f !important;
        color: #e0e0e0 !important;
    }

    /* =======================================================
       3. MÉTRICAS, ANIMACIONES Y TARJETAS BI CUSTOM
       ======================================================= */

    /* Métricas Nativas de Streamlit tipo Panel LED */
    [data-testid="stMetric"] {
        background: #0a0a0a !important;
        border: 1px solid #1f1f1f !important;
        padding: 15px !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5) !important;
        text-align: center !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stMetric"]:hover {
        border-color: #00f0ff !important;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.1) !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Fira Code', monospace !important;
        color: #00f0ff !important;
        text-shadow: 0 0 10px rgba(0, 240, 255, 0.4) !important;
    }
    [data-testid="stMetricLabel"] {
        color: #8b949e !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }

    /* Animación de Carga Cyber */
    .scanning-wrapper {
        display: flex; flex-direction: column; align-items: center; padding: 30px;
        background: #0a0a0a; border-radius: 10px; border: 1px solid #1f1f1f; margin: 20px 0;
        box-shadow: 0 0 20px rgba(0, 240, 255, 0.05);
    }
    .scan-line {
        width: 100%; height: 2px; background: #00f0ff; box-shadow: 0 0 15px #00f0ff, 0 0 30px #00f0ff;
        position: relative; animation: scan 1.5s ease-in-out infinite;
    }
    @keyframes scan { 0% { transform: translateY(0); opacity: 0.3; } 50% { transform: translateY(40px); opacity: 1; } 100% { transform: translateY(0); opacity: 0.3; } }
    .loading-step { font-family: 'Fira Code', monospace; color: #00f0ff; margin-top: 20px; font-size: 1rem; text-shadow: 0 0 5px rgba(0, 240, 255, 0.5); }
    
    /* Consola de Depuración Hacker */
    .console-box {
        background: #000000; color: #39ff14; padding: 15px; border-radius: 8px; border: 1px solid #113311;
        font-family: 'Fira Code', monospace; height: 180px; overflow-y: auto; font-size: 0.85rem;
        box-shadow: inset 0 0 15px rgba(57, 255, 20, 0.05);
    }

    /* Tarjetas Interactivas de Fase 3 */
    .quant-card {
        padding: 20px;
        border-radius: 10px;
        height: 100%;
        transition: all 0.3s ease;
        background-color: #0a0a0a;
        border: 1px solid #1f1f1f;
        position: relative;
        overflow: hidden;
    }
    .quant-card::before {
        content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; transition: all 0.3s ease;
    }
    .quant-card:hover {
        transform: translateY(-5px);
    }
    
    .card-hit { border-color: rgba(57, 255, 20, 0.2); }
    .card-hit::before { background-color: #39ff14; box-shadow: 0 0 15px #39ff14; }
    .card-hit:hover { box-shadow: 0 10px 20px rgba(57, 255, 20, 0.1); border-color: #39ff14; }
    .card-hit .card-icon { color: #39ff14; text-shadow: 0 0 8px rgba(57, 255, 20, 0.4); }
    
    .card-miss { border-color: rgba(255, 0, 60, 0.2); }
    .card-miss::before { background-color: #ff003c; box-shadow: 0 0 15px #ff003c; }
    .card-miss:hover { box-shadow: 0 10px 20px rgba(255, 0, 60, 0.1); border-color: #ff003c; }
    .card-miss .card-icon { color: #ff003c; text-shadow: 0 0 8px rgba(255, 0, 60, 0.4); }

    .card-icon { font-family: 'Fira Code', monospace; font-weight: bold; font-size: 0.9rem; margin-bottom: 10px; letter-spacing: 1px; }
    .card-title { font-size: 1.05rem; font-weight: 600; color: #ffffff; }

    /* Tablas BI Cyber-Quant */
    .bi-table-container {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #1f1f1f;
        box-shadow: 0 5px 15px rgba(0,0,0,0.5);
    }
    .bi-table { 
        width: 100%; border-collapse: collapse; font-size: 0.95rem; background-color: #0a0a0a; 
    }
    .bi-table th { 
        background-color: #111111; color: #00f0ff; padding: 15px; text-align: left; 
        border-bottom: 1px solid #1f1f1f; font-family: 'Fira Code', monospace; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;
    }
    .bi-table td { padding: 12px 15px; border-bottom: 1px solid #151515; color: #c9d1d9; }
    .bi-table tr:nth-child(even) { background-color: #0d0d0d; }
    .bi-table tr:hover { background-color: #1a1a1a; }
    
    /* Badges LED Neón para Status de Tabla */
    .status-badge {
        font-family: 'Fira Code', monospace; font-size: 0.8rem; padding: 5px 10px; border-radius: 4px; font-weight: bold; display: inline-block; letter-spacing: 0.5px;
    }
    .status-hit { 
        color: #39ff14; background: rgba(57, 255, 20, 0.1); border: 1px solid rgba(57, 255, 20, 0.3); box-shadow: 0 0 10px rgba(57, 255, 20, 0.15);
    }
    .status-miss { 
        color: #ff003c; background: rgba(255, 0, 60, 0.1); border: 1px solid rgba(255, 0, 60, 0.3); box-shadow: 0 0 10px rgba(255, 0, 60, 0.15);
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A APIS ---
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
                time.sleep(1) 
                st.rerun()
            except Exception as e:
                st.error(f"Error al borrar DB: {e}")
        else:
            st.error("No hay conexión a la base de datos.")

    st.caption("Quant/Sharp v8.7 | BI Dashboard Update")

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
        update_status_ui(status_placeholder, 1, "Leyendo PDF y estructurando KPIs...")
        time.sleep(0.5)
        update_status_ui(status_placeholder, 2, "Procesando Imagen y métricas reales...")
        time.sleep(0.5)
        update_status_ui(status_placeholder, 3, "Cruzando datos algorítmicamente...")

        # PROMPT 100% ESTANDARIZADO PARA BI
        prompt = """
        Eres un auditor estadístico experto de apuestas deportivas operando un dashboard de Business Intelligence.
        Tu tarea es cruzar los pronósticos de un informe técnico (PDF) con la realidad de un partido (Imagen Flashscore).

        REGLAS DE EXTRACCIÓN ESTRICTAS:
        1. Lee la imagen con atención para extraer: Marcador final, Goles Esperados (xG), Tiros de esquina, Tarjetas amarillas y Posesión de balón.
        
        2. EVALUACIÓN DE APUESTAS (apuestas_detalle): Evalúa OBLIGATORIAMENTE estas 3 apuestas de la Fase 3 del PDF usando lógica matemática:
           - "Menos de 2.5 Goles": hit=true SOLO SI la suma de los goles del marcador de la imagen es 0, 1 o 2.
           - "Ambos Equipos Marcan - No": hit=true SOLO SI el marcador de la imagen tiene al menos un '0'.
           - "Doble Oportunidad 1X": hit=true SOLO SI el equipo local ganó o empató según la imagen.
           
        3. COMPARATIVA DE SIMULACIÓN (comparativa_simulacion): Evalúa OBLIGATORIAMENTE estos 5 KPIs cruzando la Fase 2 del PDF contra la Imagen:
           - KPI 1 "Goles Totales": Extrae la predicción de goles del PDF vs el Marcador Real. (acerto: true si coincidió el pronóstico del ganador/empate o cantidad).
           - KPI 2 "Goles Esperados (xG)": Extrae el xG del informe vs xG de la imagen. (acerto: true si el equipo que se preveía con más xG realmente lo tuvo).
           - KPI 3 "Tiros de Esquina": Extrae estimación de córners del informe vs cantidad real en imagen.
           - KPI 4 "Tarjetas Amarillas": Extrae estimación de tarjetas del informe vs total real en imagen.
           - KPI 5 "Posesión de Balón": Extrae previsión de dominio del informe vs porcentaje real en imagen.

        4. El campo "accuracy_score" (0-100) debe ser matemático: (Apuestas hit=true / 3) * 100.

        Devuelve JSON ESTRICTAMENTE con esta estructura:
        {
          "partido": "Nombre Equipo A vs Nombre Equipo B",
          "pronostico": "Resumen general sugerido",
          "marcador_final": "Marcador extraído de la imagen (ej. 0-1)",
          "estado": "🟢 (Si accuracy_score >= 50) o 🔴 (Si accuracy_score < 50)",
          "accuracy_score": int,
          "apuestas_detalle": [
            {"apuesta": "Menos de 2.5 Goles", "hit": true o false},
            {"apuesta": "Ambos Equipos Marcan - No", "hit": true o false},
            {"apuesta": "Doble Oportunidad 1X", "hit": true o false}
          ],
          "comparativa_simulacion": [
            {"metrica": "Goles Totales", "informe": "Lo que predecía el PDF", "real": "El dato de la imagen", "acerto": true o false},
            {"metrica": "Goles Esperados (xG)", "informe": "...", "real": "...", "acerto": true o false},
            {"metrica": "Tiros de Esquina", "informe": "...", "real": "...", "acerto": true o false},
            {"metrica": "Tarjetas Amarillas", "informe": "...", "real": "...", "acerto": true o false},
            {"metrica": "Posesión de Balón", "informe": "...", "real": "...", "acerto": true o false}
          ],
          "analisis_tecnico": "Breve explicación objetiva del cruce de datos."
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
                update_status_ui(status_placeholder, 4, "Generando panel de Business Intelligence...")
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

t1, t2, t3 = st.tabs(["📄 AUDITORÍA", "🛡️ APUESTA MAESTRA", "📊 PANEL DE CONTROL BI"])

# --- TAB 1: AUDITORÍA ---
with t1:
    c1, c2 = st.columns(2)
    with c1: pdfs = st.file_uploader("PDFs", type="pdf", accept_multiple_files=True)
    with c2: imgs = st.file_uploader("Capturas Flashscore", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if st.button("▶ INICIAR AUDITORÍA ESTRUCTURADA"):
        if pdfs and imgs and len(pdfs) == len(imgs):
            for i in range(len(pdfs)):
                status_area = st.empty()
                res_raw, err = auditar_partido(pdfs[i], imgs[i], model_option, status_area)
                status_area.empty()
                
                if not err and res_raw:
                    try:
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
                            st.json(row) 
                            
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

# --- TAB 3: DASHBOARD BI ---
with t3:
    col_ref, empty_col = st.columns([1, 4])
    with col_ref:
        if st.button("🔄 Refrescar Tablero"):
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
                        
                        # Título del Expander con datos rápidos
                        expander_title = f"{row.get('estado', '⚪')} {row.get('partido', 'Unknown')} | Marcador Real: {row.get('marcador_final', 'N/A')} | {row['fecha'].strftime('%d/%m %H:%M')}"
                        
                        with st.expander(expander_title, expanded=False):
                            
                            st.write(f"**Nivel de Precisión (Accuracy):** {data.get('accuracy_score', 0)}%")
                            
                            # ==========================================
                            # BLOQUE 1: TARJETAS DE APUESTAS (BI CARDS)
                            # ==========================================
                            st.markdown("##### 🎯 Apuestas Estratégicas (Fase 3)")
                            apuestas = data.get('apuestas_detalle', [])
                            
                            if apuestas:
                                # Creamos columnas dinámicas según la cantidad de apuestas
                                cols_apuestas = st.columns(len(apuestas))
                                for idx, b in enumerate(apuestas):
                                    is_hit = b.get("hit", False)
                                    
                                    # Asignación de clases y variables visuales
                                    card_class = "card-hit" if is_hit else "card-miss"
                                    icon = "[ ✓ ] HIT VALIDADO" if is_hit else "[ ✗ ] MISS DETECTADO"
                                    txt_apuesta = b.get("apuesta", "Apuesta")
                                    
                                    # Tarjeta HTML/CSS Inyectada
                                    card_html = f"""
                                    <div class="quant-card {card_class}">
                                        <div class="card-icon">{icon}</div>
                                        <div class="card-title">{txt_apuesta}</div>
                                    </div>
                                    """
                                    cols_apuestas[idx].markdown(card_html, unsafe_allow_html=True)
                            else:
                                st.write("No se encontraron detalles de apuestas.")

                            st.write("") # Espaciador
                            st.write("") 

                            # ==========================================
                            # BLOQUE 2: TABLA DE KPIs (LOOKER STYLE)
                            # ==========================================
                            st.markdown("##### 📊 Desglose de Simulaciones (Fase 2)")
                            
                            # Construcción de la tabla HTML
                            html_table = "<div class='bi-table-container'><table class='bi-table'>"
                            html_table += "<tr><th>Métrica Analizada</th><th>Predicción (Informe)</th><th>Realidad (Imagen)</th><th>Status</th></tr>"
                            
                            for sim in data.get('comparativa_simulacion', []):
                                acerto = sim.get('acerto', False)
                                status_html = "<span class='status-badge status-hit'>[ ✓ ] MATCH</span>" if acerto else "<span class='status-badge status-miss'>[ ✗ ] FAIL</span>"
                                metrica = sim.get('metrica', 'Métrica')
                                informe = sim.get('informe', 'N/A')
                                real = sim.get('real', 'N/A')
                                
                                html_table += f"<tr><td><b>{metrica}</b></td><td>{informe}</td><td>{real}</td><td>{status_html}</td></tr>"
                            
                            html_table += "</table></div>"
                            st.markdown(html_table, unsafe_allow_html=True)
                            
                            # ==========================================
                            # RESUMEN Y ACCIONES
                            # ==========================================
                            if "analisis_tecnico" in data:
                                st.write("")
                                st.info(f"**Análisis de Desviación Técnica:** {data['analisis_tecnico']}")
                                
                            col_del, _ = st.columns([1, 5])
                            with col_del:
                                if st.button("🗑️ Eliminar Registro", key=f"del_{row['id']}"):
                                    supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                                    st.rerun()
                                    
                    except Exception as e:
                        st.error(f"Fila ID {row.get('id')} corrupta. Error: {e}")
                        if st.button(f"Limpiar Registro #{row.get('id')}", key=f"fix_{row.get('id')}"):
                            supabase.table("auditoria_apuestas").delete().eq("id", row['id']).execute()
                            st.rerun()
            else: 
                st.info("Base de datos vacía. Sube tus PDFs y Capturas en la pestaña de Auditoría.")
        else:
            st.error("No se pudo conectar a Supabase. Revisa las credenciales.")
    except Exception as e: 
        st.error(f"Error de conexión con Supabase o procesando DB: {e}")
