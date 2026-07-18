import sqlite3
from datetime import datetime
from engine_v1 import APEngineV1
from db_setup import crear_base_de_datos

def pedir_numero(mensaje, tipo=float, valor_defecto=0.0):
    """
    Función auxiliar para pedir números por consola sin que el programa colapse
    si te equivocas al teclear.
    """
    while True:
        entrada = input(f"{mensaje} [Defecto: {valor_defecto}]: ").strip()
        if not entrada:
            return valor_defecto
        try:
            return tipo(entrada)
        except ValueError:
            print(f"❌ Error: Debes ingresar un valor numérico válido para {tipo.__name__}.")

def ingresar_partido_interactivo():
    print("\n" + "="*60)
    print("🚀 AP ENGINE 1.0 | INGRESO Y ANÁLISIS DE PARTIDO")
    print("="*60)
    
    # 1. Datos Generales
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    fecha = input(f"📅 Fecha del partido (YYYY-MM-DD) [{fecha_hoy}]: ").strip() or fecha_hoy
    liga = input("🏆 Liga o Competición (Ej. LigaPro, Champions, Premier): ").strip() or "General"
    local = input("🏠 Equipo Local: ").strip() or "Local"
    visita = input("✈️ Equipo Visitante: ").strip() or "Visitante"
    
    print(f"\n--- 📈 ESTADÍSTICAS RECIENTES DE {local.upper()} (LOCAL) ---")
    goles_l = pedir_numero("Promedio de Goles Anotados", float, 1.5)
    tiros_l = pedir_numero("Promedio de Tiros a Puerta", float, 4.5)
    corners_l = pedir_numero("Promedio de Córners", float, 5.0)
    lesiones_l = pedir_numero("Lesiones de jugadores clave (0, 1, 2...)", int, 0)
    
    print(f"\n--- 📉 ESTADÍSTICAS RECIENTES DE {visita.upper()} (VISITANTE) ---")
    goles_v = pedir_numero("Promedio de Goles Anotados", float, 1.2)
    tiros_v = pedir_numero("Promedio de Tiros a Puerta", float, 3.8)
    corners_v = pedir_numero("Promedio de Córners", float, 4.0)
    lesiones_v = pedir_numero("Lesiones de jugadores clave (0, 1, 2...)", int, 0)
    
    print("\n--- 💰 CUOTAS DE LA CASA DE APUESTAS ---")
    cuota_l = pedir_numero(f"Cuota para victoria de {local}", float, 2.00)
    cuota_e = pedir_numero("Cuota para el Empate", float, 3.30)
    cuota_v = pedir_numero(f"Cuota para victoria de {visita}", float, 3.50)
    
    # 2. Llamar al cerebro del AP Engine v1.0 para analizar el partido
    motor = APEngineV1()
    stats_local = (goles_l, tiros_l, corners_l, lesiones_l)
    stats_visita = (goles_v, tiros_v, corners_v, lesiones_v)
    cuotas = {'local': cuota_l, 'empate': cuota_e, 'visita': cuota_v}
    
    resultado_engine = motor.analizar_partido(local, visita, stats_local, stats_visita, cuotas)
    
    # 3. Guardar todo en la base de datos SQLite
    print("⏳ Guardando partido y predicción en 'ap_engine.db'...")
    crear_base_de_datos()
    conn = sqlite3.connect('data/ap_engine.db')
    cursor = conn.cursor()
    
    try:
        # Insertar el partido (Entradas)
        cursor.execute('''
        INSERT INTO partidos (
            fecha, liga, equipo_local, equipo_visitante,
            goles_prom_local, goles_prom_visita, tiros_prom_local, tiros_prom_visita,
            corners_prom_local, corners_prom_visita, lesiones_clave_local, lesiones_clave_visita
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha, liga, local, visita, goles_l, goles_v, tiros_l, tiros_v, corners_l, corners_v, lesiones_l, lesiones_v))
        
        id_partido_creado = cursor.lastrowid
        
        # Insertar la predicción del motor (Salidas)
        cursor.execute('''
        INSERT INTO historial_predicciones (
            id_partido, version_engine, prob_local, prob_empate, prob_visita,
            cuota_bookie_local, cuota_bookie_empate, cuota_bookie_visita,
            ev_local, apuesta_recomendada, kelly_stake_sugerido
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_partido_creado, 'v1.0', 
            resultado_engine['prob_local'], resultado_engine['prob_empate'], resultado_engine['prob_visita'],
            cuota_l, cuota_e, cuota_v,
            resultado_engine['ev_local'], resultado_engine['apuesta'], resultado_engine['stake']
        ))
        
        conn.commit()
        print(f"✅ ¡Éxito! Partido guardado con ID #{id_partido_creado} y enlazado al historial del motor.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al guardar en base de datos: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    ingresar_partido_interactivo()