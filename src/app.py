import streamlit as st
import sqlite3
import pandas as pd
from engine_v1 import APEngineV1
from engine_v3_ml import APEngineV3ML  # <-- 1. Importamos la IA de XGBoost
from extractor_stats import ExtractorAPI
from db_setup import crear_base_de_datos
from modulo_elo import SistemaElo

# Configuración de la página web
st.set_page_config(page_title="AP Engine Full-Stack", page_icon="⚽", layout="wide")

# Asegurar que la base de datos exista
crear_base_de_datos()

def conectar_db():
    return sqlite3.connect('data/ap_engine.db')

# Título Principal
st.title("⚽ AP Engine | Plataforma Cuantitativa y Machine Learning")
st.markdown("---")

# Crear las 4 pestañas del sistema
tab_dashboard, tab_analizador, tab_historial, tab_elo = st.tabs([
    "📊 Dashboard ROI", 
    "🔮 Analizador en Vivo (Dual Engine)", 
    "🗄️ Historial de Partidos",
    "🏆 Ranking Elo de la Liga"
])

# ==========================================
# PESTAÑA 1: DASHBOARD DE RENDIMIENTO (ROI)
# ==========================================
with tab_dashboard:
    st.header("Rendimiento Histórico y Finanzas del Motor")
    conn = conectar_db()
    query = '''
    SELECT cuota_bookie_local, cuota_bookie_empate, cuota_bookie_visita, 
           apuesta_recomendada, kelly_stake_sugerido, resultado_apuesta
    FROM historial_predicciones
    WHERE resultado_apuesta IS NOT NULL AND resultado_apuesta != 'NULA (Sin apuesta)'
    '''
    try:
        df_roi = pd.read_sql_query(query, conn)
    except Exception:
        df_roi = pd.DataFrame()
    conn.close()
    
    if df_roi.empty:
        st.info("ℹ️ Aún no tienes apuestas evaluadas para calcular el ROI.")
    else:
        total_apuestas = len(df_roi)
        ganadas = len(df_roi[df_roi['resultado_apuesta'] == 'GANADA'])
        win_rate = (ganadas / total_apuestas) * 100
        capital_invertido = df_roi['kelly_stake_sugerido'].sum()
        retorno_total = 0.0
        
        for idx, row in df_roi.iterrows():
            if row['resultado_apuesta'] == 'GANADA':
                if "LOCAL" in row['apuesta_recomendada']: cuota = row['cuota_bookie_local']
                elif "VISITANTE" in row['apuesta_recomendada']: cuota = row['cuota_bookie_visita']
                else: cuota = row['cuota_bookie_empate']
                retorno_total += (row['kelly_stake_sugerido'] * cuota)
                
        ganancia_neta = retorno_total - capital_invertido
        roi = (ganancia_neta / capital_invertido * 100) if capital_invertido > 0 else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Apuestas Evaluadas", f"{total_apuestas}", f"{ganadas} Ganadas")
        col2.metric("Win Rate (Aciertos)", f"{win_rate:.1f}%")
        col3.metric("Capital Invertido", f"${capital_invertido:.2f} USD")
        col4.metric("ROI del Motor", f"{roi:+.2f}%", f"${ganancia_neta:+.2f} USD", delta_color="normal")

# ==========================================
# PESTAÑA 2: ANALIZADOR DUAL (V2.0 vs V3.0)
# ==========================================
with tab_analizador:
    st.header("Escáner Predictivo Multi-Mercado")
    
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("Configuración de Entrada")
        
        # SELECTOR DE MOTOR ALGORÍTMICO
        motor_elegido = st.radio(
            "🧠 Selecciona el Motor Predictivo a utilizar:",
            ["🧬 V2.0 Cuantitativo (Dixon-Coles + Elo)", "🤖 V3.0 Machine Learning (XGBoost AI)"],
            horizontal=True
        )
        st.markdown("---")
        
        equipo_local = st.selectbox("Equipo Local", ["Barcelona SC", "Real Madrid", "Liga de Quito", "Manchester City", "Arsenal", "Otro"])
        if equipo_local == "Otro": equipo_local = st.text_input("Nombre Equipo Local", "Local")
            
        equipo_visita = st.selectbox("Equipo Visitante", ["Emelec", "Real Sociedad", "Manchester United", "Chelsea", "Otro"], index=0)
        if equipo_visita == "Otro": equipo_visita = st.text_input("Nombre Equipo Visitante", "Visitante")
            
        st.markdown("#### Cuotas de Apuesta")
        c1, c2, c3 = st.columns(3)
        cuota_l = c1.number_input(f"Victoria {equipo_local}", value=2.00, step=0.05)
        cuota_e = c2.number_input("Empate", value=3.30, step=0.05)
        cuota_v = c3.number_input(f"Victoria {equipo_visita}", value=3.50, step=0.05)
        
        c4, c5, c6, c7 = st.columns(4)
        cuota_ov_g = c4.number_input("Over 2.5 Goles", value=1.95, step=0.05)
        cuota_un_g = c5.number_input("Under 2.5 Goles", value=1.85, step=0.05)
        cuota_ov_c = c6.number_input("Over 9.5 Córners", value=2.10, step=0.05)
        cuota_un_c = c7.number_input("Under 9.5 Córners", value=1.70, step=0.05)
        
        analizar_btn = st.button("🚀 Ejecutar Predicción", type="primary", use_container_width=True)
        
    with col_der:
        if analizar_btn:
            st.subheader("Pronóstico y Detección de Valor")
            motor_v1 = APEngineV1() # Usamos V1 como base cuantitativa y para helpers de Kelly
            elo_sys = SistemaElo()
            
            with st.spinner("Procesando matemáticas y consultando bases de datos..."):
                base_equipos = {
                    "barcelona sc": (1.9, 6.2, 5.8, 0), "emelec": (1.2, 4.1, 4.5, 1),
                    "liga de quito": (1.8, 5.5, 6.0, 0), "real madrid": (2.4, 7.5, 6.8, 1),
                    "manchester city": (2.6, 8.0, 7.5, 0), "arsenal": (2.1, 6.8, 6.5, 0),
                    "chelsea": (1.5, 5.0, 5.5, 1)
                }
                stats_l = base_equipos.get(equipo_local.lower(), (1.6, 5.0, 5.5, 0))
                stats_v = base_equipos.get(equipo_visita.lower(), (1.2, 3.8, 4.0, 0))
                cuotas = {'local': cuota_l, 'empate': cuota_e, 'visita': cuota_v, 'over_25': cuota_ov_g, 'under_25': cuota_un_g, 'over_corners': cuota_ov_c, 'under_corners': cuota_un_c}
                
                elo_l = elo_sys.obtener_elo(equipo_local)
                elo_v = elo_sys.obtener_elo(equipo_visita)
                st.write(f"🏆 **Prestigio Elo en SQLite:** `{equipo_local} ({elo_l:.1f} pts)` vs `{equipo_visita} ({elo_v:.1f} pts)`")
                st.write("---")
                
                # BIFURCACIÓN DE LÓGICA SEGÚN EL MOTOR ELEGIDO
                if "V2.0" in motor_elegido:
                    st.info("⚙️ **Calculando con Motor V2.0:** Covarianza de Dixon-Coles + Modulador Elo.")
                    res = motor_v1.analizar_partido(equipo_local, equipo_visita, stats_l, stats_v, cuotas)
                    p_l, p_e, p_v = res['prob_local'], res['prob_empate'], res['prob_visita']
                    ev_l, apuesta, stake = res['ev_local'], res['apuesta'], res['stake']
                else:
                    st.success("🤖 **Calculando con Motor V3.0:** Árboles de Decisión XGBoost entrenados en SQLite.")
                    ai_engine = APEngineV3ML()
                    probs_ml = ai_engine.predecir_partido_ml(stats_l, stats_v)
                    p_l, p_e, p_v = probs_ml['prob_local'], probs_ml['prob_empate'], probs_ml['prob_visita']
                    
                    # Reutilizamos el evaluador financiero de Kelly para la IA
                    ev_l, _, stake_l = motor_v1.evaluar_valor_y_kelly(p_l, cuota_l)
                    ev_e, _, stake_e = motor_v1.evaluar_valor_y_kelly(p_e, cuota_e)
                    ev_v, _, stake_v = motor_v1.evaluar_valor_y_kelly(p_v, cuota_v)
                    
                    if ev_l > 0: apuesta, stake = f"VICTORIA LOCAL ({equipo_local}) @ {cuota_l}", stake_l
                    elif ev_v > 0: apuesta, stake = f"VICTORIA VISITANTE ({equipo_visita}) @ {cuota_v}", stake_v
                    elif ev_e > 0: apuesta, stake = f"EMPATE @ {cuota_e}", stake_e
                    else: apuesta, stake = "NINGUNA (Mercado eficiente)", 0.0
                
                # VISUALIZACIÓN DE BARRAS
                st.write(f"🏠 **{equipo_local}: {p_l}%** (EV Local: `{ev_l:+.2f}%`)")
                st.progress(float(p_l) / 100.0)
                
                st.write(f"🤝 **Empate: {p_e}%**")
                st.progress(float(p_e) / 100.0)
                
                st.write(f"✈️ **{equipo_visita}: {p_v}%**")
                st.progress(float(p_v) / 100.0)
                st.write("---")
                
                if "NINGUNA" not in apuesta:
                    st.success(f"🎯 **PICK RECOMENDADO (EV+):** {apuesta}\n\n💰 **Stake Sugerido (Half-Kelly):** `${stake} USD`")
                else:
                    st.warning("⚠️ **SIN VALOR MATEMÁTICO:** Las cuotas de la casa de apuestas absorben la probabilidad. No arriesgar capital.")

# ==========================================
# PESTAÑA 3: HISTORIAL DE PARTIDOS
# ==========================================
with tab_historial:
    st.header("Base de Datos SQLite (Historial Inmutable)")
    conn = conectar_db()
    try:
        df_hist = pd.read_sql_query('''
        SELECT id_partido as ID, fecha as Fecha, liga as Torneo, equipo_local as Local, equipo_visitante as Visita, 
               goles_real_local as "Goles L", goles_real_visita as "Goles V", estatus as Estatus
        FROM partidos ORDER BY id_partido DESC LIMIT 100
        ''', conn)
        st.dataframe(df_hist, use_container_width=True)
    except Exception: st.write("No hay datos disponibles.")
    conn.close()

# ==========================================
# PESTAÑA 4: RANKING ELO DE LA LIGA
# ==========================================
with tab_elo:
    st.header("🏆 Puntuación Elo Dinámica de los Clubes")
    conn = conectar_db()
    try:
        df_elo = pd.read_sql_query('''
        SELECT UPPER(equipo) as "Equipo / Club", ROUND(puntuacion_elo, 1) as "Puntuación Elo (pts)", 
               partidos_jugados as "Partidos en BD", ultima_actualizacion as "Última Actualización"
        FROM ranking_elo ORDER BY puntuacion_elo DESC
        ''', conn)
        if not df_elo.empty:
            st.dataframe(df_elo, use_container_width=True)
            st.subheader("Top 15 Equipos de Mayor Prestigio en BD")
            st.bar_chart(data=df_elo.head(15).set_index("Equipo / Club")["Puntuación Elo (pts)"])
        else: st.info("El ranking aparecerá al procesar partidos.")
    except Exception as e: st.error(f"Error: {e}")
    finally: conn.close()