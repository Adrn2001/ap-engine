import streamlit as st
import sqlite3
import pandas as pd
from engine_v1 import APEngineV1
from extractor_stats import ExtractorAPI
from db_setup import crear_base_de_datos
from modulo_elo import SistemaElo

# Configuración de la página web
st.set_page_config(page_title="AP Engine 2.0", page_icon="🧬", layout="wide")

# Asegurar que la base de datos exista
crear_base_de_datos()

def conectar_db():
    return sqlite3.connect('data/ap_engine.db')

# Título Principal
st.title("🧬 AP Engine 2.0 | Cuantitativo: Dixon-Coles + Elo + xG")
st.markdown("---")

# Crear 4 pestañas de navegación
tab_dashboard, tab_analizador, tab_historial, tab_elo = st.tabs([
    "📊 Dashboard ROI", 
    "🔮 Analizador en Vivo (v2.0)", 
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
        st.info("ℹ️ Aún no tienes apuestas finalizadas y evaluadas para calcular el ROI.")
        st.write("💡 *Ejecuta `python src/evaluar_rendimiento.py` al terminar tus partidos para ver las finanzas en vivo aquí.*")
    else:
        total_apuestas = len(df_roi)
        ganadas = len(df_roi[df_roi['resultado_apuesta'] == 'GANADA'])
        win_rate = (ganadas / total_apuestas) * 100
        
        capital_invertido = df_roi['kelly_stake_sugerido'].sum()
        retorno_total = 0.0
        
        for idx, row in df_roi.iterrows():
            if row['resultado_apuesta'] == 'GANADA':
                if "LOCAL" in row['apuesta_recomendada']:
                    cuota = row['cuota_bookie_local']
                elif "VISITANTE" in row['apuesta_recomendada']:
                    cuota = row['cuota_bookie_visita']
                else:
                    cuota = row['cuota_bookie_empate']
                retorno_total += (row['kelly_stake_sugerido'] * cuota)
                
        ganancia_neta = retorno_total - capital_invertido
        roi = (ganancia_neta / capital_invertido * 100) if capital_invertido > 0 else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Apuestas Evaluadas", f"{total_apuestas}", f"{ganadas} Ganadas")
        col2.metric("Win Rate (Aciertos)", f"{win_rate:.1f}%")
        col3.metric("Capital Invertido", f"${capital_invertido:.2f} USD")
        col4.metric("ROI del Motor", f"{roi:+.2f}%", f"${ganancia_neta:+.2f} USD", delta_color="normal")

# ==========================================
# PESTAÑA 2: ANALIZADOR EN VIVO (V2.0)
# ==========================================
with tab_analizador:
    st.header("Escáner Multi-Mercado con Modelo Dixon-Coles y Elo")
    
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("Configuración del Partido")
        equipo_local = st.selectbox("Equipo Local", ["Barcelona SC", "Real Madrid", "Liga de Quito", "Manchester City", "Independiente del Valle", "Otro"])
        if equipo_local == "Otro":
            equipo_local = st.text_input("Nombre Equipo Local", "Local")
            
        equipo_visita = st.selectbox("Equipo Visitante", ["Emelec", "Real Sociedad", "Manchester United", "Otro"], index=0)
        if equipo_visita == "Otro":
            equipo_visita = st.text_input("Nombre Equipo Visitante", "Visitante")
            
        st.markdown("#### Cuotas de la Casa de Apuestas")
        c1, c2, c3 = st.columns(3)
        cuota_l = c1.number_input(f"Victoria {equipo_local}", value=2.00, step=0.05)
        cuota_e = c2.number_input("Empate", value=3.30, step=0.05)
        cuota_v = c3.number_input(f"Victoria {equipo_visita}", value=3.50, step=0.05)
        
        c4, c5, c6, c7 = st.columns(4)
        cuota_ov_g = c4.number_input("Over 2.5 Goles", value=1.95, step=0.05)
        cuota_un_g = c5.number_input("Under 2.5 Goles", value=1.85, step=0.05)
        cuota_ov_c = c6.number_input("Over 9.5 Córners", value=2.10, step=0.05)
        cuota_un_c = c7.number_input("Under 9.5 Córners", value=1.70, step=0.05)
        
        analizar_btn = st.button("🚀 Ejecutar Algoritmo 2.0", type="primary", use_container_width=True)
        
    with col_der:
        if analizar_btn:
            st.subheader("Pronóstico y Detección de Valor")
            motor = APEngineV1()
            elo_sys = SistemaElo()
            
            with st.spinner("Procesando covarianzas de Dixon-Coles y consultando ranking en SQLite..."):
                base_equipos = {
                    "barcelona sc": (1.9, 6.2, 5.8, 0),
                    "emelec": (1.2, 4.1, 4.5, 1),
                    "liga de quito": (1.8, 5.5, 6.0, 0),
                    "real madrid": (2.4, 7.5, 6.8, 1),
                    "manchester city": (2.6, 8.0, 7.5, 0),
                    "real sociedad": (1.1, 3.2, 4.0, 0)
                }
                stats_l = base_equipos.get(equipo_local.lower(), (1.5, 4.5, 5.0, 0))
                stats_v = base_equipos.get(equipo_visita.lower(), (1.2, 3.8, 4.0, 0))
                
                cuotas = {
                    'local': cuota_l, 'empate': cuota_e, 'visita': cuota_v,
                    'over_25': cuota_ov_g, 'under_25': cuota_un_g,
                    'over_corners': cuota_ov_c, 'under_corners': cuota_un_c
                }
                res = motor.analizar_partido(equipo_local, equipo_visita, stats_l, stats_v, cuotas)
                
                elo_l = elo_sys.obtener_elo(equipo_local)
                elo_v = elo_sys.obtener_elo(equipo_visita)
                st.write(f"🏆 **Prestigio Elo:** `{equipo_local} ({elo_l:.1f} pts)` vs `{equipo_visita} ({elo_v:.1f} pts)`")
                
                st.write("---")
                st.write(f"🏠 **{equipo_local}: {res['prob_local']}%** (EV: `{res['ev_local']:+.2f}%`)")
                st.progress(res['prob_local'] / 100)
                
                st.write(f"🤝 **Empate (Ajustado D-C): {res['prob_empate']}%**")
                st.progress(res['prob_empate'] / 100)
                
                st.write(f"✈️ **{equipo_visita}: {res['prob_visita']}%**")
                st.progress(res['prob_visita'] / 100)
                
                st.write("---")
                if "NINGUNA" not in res['apuesta']:
                    st.success(f"🎯 **PICK NÚMERO #1 (EV+):** {res['apuesta']}\n\n💰 **Stake Sugerido (Half-Kelly):** `${res['stake']} USD`")
                else:
                    st.warning("⚠️ **SIN VALOR SUFICIENTE:** El mercado está perfectamente ajustado por la casa. Recomendación: NO APOSTAR.")

# ==========================================
# PESTAÑA 3: HISTORIAL DE PARTIDOS
# ==========================================
with tab_historial:
    st.header("Base de Datos del Proyecto AP")
    conn = conectar_db()
    try:
        df_hist = pd.read_sql_query('''
        SELECT p.id_partido as ID, p.fecha as Fecha, p.equipo_local as Local, p.equipo_visitante as Visita, 
               h.version_engine as Motor, h.apuesta_recomendada as Apuesta, h.kelly_stake_sugerido as Stake, p.estatus as Estatus
        FROM partidos p JOIN historial_predicciones h ON p.id_partido = h.id_partido
        ORDER BY p.id_partido DESC
        ''', conn)
        st.dataframe(df_hist, use_container_width=True)
    except Exception:
        st.write("No hay datos disponibles aún.")
    conn.close()

# ==========================================
# PESTAÑA 4: RANKING ELO DE LA LIGA (NUEVO V2.0)
# ==========================================
with tab_elo:
    st.header("🏆 Tabla de Posiciones y Puntuación Elo Dinámica")
    st.write("Esta tabla se reconfigura automáticamente en tu base de datos cada vez que evalúas un partido finalizado.")
    
    conn = conectar_db()
    try:
        df_elo = pd.read_sql_query('''
        SELECT UPPER(equipo) as "Equipo / Club", 
               ROUND(puntuacion_elo, 1) as "Puntuación Elo (pts)", 
               partidos_jugados as "Partidos Jugados en BD", 
               ultima_actualizacion as "Último Cambio"
        FROM ranking_elo
        ORDER BY puntuacion_elo DESC
        ''', conn)
        
        if df_elo.empty:
            st.info("ℹ️ El ranking aún está en blanco. En cuanto proceses tu primer partido con el motor, los equipos aparecerán aquí con 1500 puntos.")
        else:
            # Mostrar tabla interactiva de posiciones
            st.dataframe(df_elo, use_container_width=True)
            
            # Gráfico de barras de los equipos del ranking
            st.subheader("Gráfico de Prestigio (Top Equipos)")
            st.bar_chart(data=df_elo.set_index("Equipo / Club")["Puntuación Elo (pts)"])
            
    except Exception as e:
        st.error(f"Error al cargar la tabla Elo: {e}")
    finally:
        conn.close()