import streamlit as st
import sqlite3
import pandas as pd
from engine_v1 import APEngineV1
from extractor_stats import ExtractorAPI
from db_setup import crear_base_de_datos

# Configuración de la página web
st.set_page_config(page_title="AP Engine", page_icon="⚽", layout="wide")

# Asegurar que la base de datos exista
crear_base_de_datos()

def conectar_db():
    return sqlite3.connect('data/ap_engine.db')

# Título Principal
st.title("⚽ AP Engine | Motor de Ciencia de Datos & Predicción Deportiva")
st.markdown("---")

# Crear pestañas de navegación
tab_dashboard, tab_analizador, tab_historial = st.tabs(["📊 Dashboard ROI", "🔮 Analizador en Vivo", "🗄️ Historial de Partidos"])

# ==========================================
# PESTAÑA 1: DASHBOARD DE RENDIMIENTO (ROI)
# ==========================================
with tab_dashboard:
    st.header("Rendimiento Histórico del Modelo")
    
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
        st.info("ℹ️ Aún no tienes partidos finalizados y evaluados en la base de datos para calcular el ROI.")
        st.write("💡 *Ve a la terminal y ejecuta `python src/evaluar_rendimiento.py` cuando terminen tus partidos para ver las métricas aquí.*")
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
        
        # Tarjetas de Métricas en columnas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Apuestas Evaluadas", f"{total_apuestas}", f"{ganadas} Ganadas")
        col2.metric("Win Rate (Aciertos)", f"{win_rate:.1f}%")
        col3.metric("Capital Invertido", f"${capital_invertido:.2f} USD")
        col4.metric("ROI del Motor", f"{roi:+.2f}%", f"${ganancia_neta:+.2f} USD", delta_color="normal")

# ==========================================
# PESTAÑA 2: ANALIZADOR DE PARTIDOS EN VIVO
# ==========================================
with tab_analizador:
    st.header("Análisis de Partido y Detección de Valor")
    
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("Configuración del Partido")
        equipo_local = st.selectbox("Equipo Local", ["Barcelona SC", "Real Madrid", "Manchester City", "Liga de Quito", "Independiente del Valle", "Otro"])
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
        
        analizar_btn = st.button("🚀 Analizar con AP Engine", type="primary", use_container_width=True)
        
    with col_der:
        if analizar_btn:
            st.subheader("Resultados del Algoritmo v1.0")
            api = ExtractorAPI()
            motor = APEngineV1()
            
            with st.spinner("Descargando estadísticas y corriendo simulaciones de Monte Carlo..."):
                # Búsqueda automática en nuestra base
                base_equipos = {
                    "barcelona sc": (1.9, 6.2, 5.8, 0),
                    "emelec": (1.2, 4.1, 4.5, 1),
                    "real madrid": (2.4, 7.5, 6.8, 1),
                    "manchester city": (2.6, 8.0, 7.5, 0),
                    "real sociedad": (1.1, 3.2, 4.0, 0)
                }
                stats_l = base_equipos.get(equipo_local.lower(), (1.5, 4.5, 5.0, 0))
                stats_v = base_equipos.get(equipo_visita.lower(), (1.2, 3.8, 4.0, 0))
                
                cuotas = {'local': cuota_l, 'empate': cuota_e, 'visita': cuota_v}
                res = motor.analizar_partido(equipo_local, equipo_visita, stats_l, stats_v, cuotas)
                
                # Mostrar barras de probabilidad visuales
                st.write("**Probabilidades Calculadas vs Implícitas:**")
                
                # Barras de progreso por opción
                st.write(f"🏠 **{equipo_local}: {res['prob_local']}%** (EV: `{res['ev_local']:+.2f}%`)")
                st.progress(res['prob_local'] / 100)
                
                st.write(f"🤝 **Empate: {res['prob_empate']}%**")
                st.progress(res['prob_empate'] / 100)
                
                st.write(f"✈️ **{equipo_visita}: {res['prob_visita']}%**")
                st.progress(res['prob_visita'] / 100)
                
                st.markdown("---")
                if "VICTORIA" in res['apuesta'] or "EMPATE" in res['apuesta']:
                    st.success(f"🎯 **RECOMENDACIÓN:** {res['apuesta']}\n\n💰 **Stake Sugerido (Kelly):** `${res['stake']} USD`")
                else:
                    st.warning("⚠️ **SIN VALOR:** Las cuotas no ofrecen un valor esperado positivo. Se recomienda no apostar.")

# ==========================================
# PESTAÑA 3: HISTORIAL DE PARTIDOS
# ==========================================
with tab_historial:
    st.header("Base de Datos del Proyecto AP")
    conn = conectar_db()
    try:
        df_hist = pd.read_sql_query('''
        SELECT p.id_partido as ID, p.fecha as Fecha, p.equipo_local as Local, p.equipo_visitante as Visita, 
               h.prob_local as "Prob. Local (%)", h.apuesta_recomendada as Apuesta, h.kelly_stake_sugerido as Stake, p.estatus as Estatus
        FROM partidos p JOIN historial_predicciones h ON p.id_partido = h.id_partido
        ORDER BY p.id_partido DESC
        ''', conn)
        st.dataframe(df_hist, use_container_width=True)
    except Exception:
        st.write("No hay datos disponibles.")
    conn.close()