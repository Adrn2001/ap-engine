import sqlite3
from datetime import datetime
from engine_v1 import APEngineV1
from db_setup import crear_base_de_datos
from extractor_stats import ExtractorAPI  # <-- 1. Importamos nuestro módulo de extracción

def pedir_numero(mensaje, tipo=float, valor_defecto=0.0):
    """Auxiliar para pedir números por consola sin que colapse por errores de tipeo."""
    while True:
        entrada = input(f"{mensaje} [Defecto: {valor_defecto}]: ").strip()
        if not entrada:
            return valor_defecto
        try:
            return tipo(entrada)
        except ValueError:
            print(f"❌ Error: Debes ingresar un valor numérico válido para {tipo.__name__}.")

def obtener_estadísticas_automatizadas(nombre_equipo, api, rol):
    """
    Busca los datos del equipo de forma automática. Si el equipo no está en la base de datos
    de la API o si el usuario prefiere hacerlo manual, activa el modo manual al instante.
    """
    print(f"\n⏳ Consultando API/Scraper en la nube para {nombre_equipo.upper()} ({rol})...")
    
    # 2. Simulamos la búsqueda por nombre en nuestra API (puedes agregar más equipos aquí)
    base_de_equipos_conocidos = {
        "barcelona sc": {"goles": 1.9, "tiros": 6.2, "corners": 5.8, "lesiones": 0},
        "emelec": {"goles": 1.2, "tiros": 4.1, "corners": 4.5, "lesiones": 1},
        "liga de quito": {"goles": 1.8, "tiros": 5.5, "corners": 6.0, "lesiones": 0},
        "independiente del valle": {"goles": 2.1, "tiros": 6.8, "corners": 6.5, "lesiones": 0},
        "real madrid": {"goles": 2.4, "tiros": 7.5, "corners": 6.8, "lesiones": 1},
        "manchester city": {"goles": 2.6, "tiros": 8.0, "corners": 7.5, "lesiones": 0}
    }
    
    nombre_normalizado = nombre_equipo.strip().lower()
    
    # Si encontramos el equipo en nuestra "nube", devolvemos los datos automáticos
    if nombre_normalizado in base_de_equipos_conocidos:
        datos = base_de_equipos_conocidos[nombre_normalizado]
        print(f"✅ ¡Datos descargados para {nombre_equipo.upper()}! -> Goles: {datos['goles']} | Tiros: {datos['tiros']} | Córners: {datos['corners']} | Lesiones: {datos['lesiones']}")
        return (datos['goles'], datos['tiros'], datos['corners'], datos['lesiones'])
    
    # Sistema de Rescate: Si la API no lo conoce, pedimos los datos a mano
    print(f"⚠️ Equipo '{nombre_equipo}' no encontrado en la consulta web automática.")
    print("👉 Activando modo de ingreso manual:")
    goles = pedir_numero(f"   Promedio de Goles de {nombre_equipo}", float, 1.5)
    tiros = pedir_numero(f"   Promedio de Tiros a Puerta de {nombre_equipo}", float, 4.5)
    corners = pedir_numero(f"   Promedio de Córners de {nombre_equipo}", float, 5.0)
    lesiones = pedir_numero(f"   Lesiones de jugadores clave en {nombre_equipo} (0, 1, 2...)", int, 0)
    
    return (goles, tiros, corners, lesiones)

def ingresar_partido_interactivo():
    print("\n" + "="*60)
    print("🚀 AP ENGINE 1.0 | INGRESO AUTOMATIZADO DE PARTIDO (ETL)")
    print("="*60)
    
    # 1. Datos Generales
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    fecha = input(f"📅 Fecha del partido (YYYY-MM-DD) [{fecha_hoy}]: ").strip() or fecha_hoy
    liga = input("🏆 Competición (Ej. LigaPro, Champions, Premier): ").strip() or "General"
    local = input("🏠 Equipo Local (Ej. Barcelona SC, Real Madrid): ").strip() or "Local"
    visita = input("✈️ Equipo Visitante (Ej. Emelec, Manchester City): ").strip() or "Visitante"
    
    # 2. Inicializamos el extractor web y buscamos los datos automáticamente
    api_web = ExtractorAPI()
    stats_local = obtener_estadísticas_automatizadas(local, api_web, "LOCAL")
    stats_visita = obtener_estadísticas_automatizadas(visita, api_web, "VISITANTE")
    
    # 3. Solo pedimos a mano lo que cambia en cada partido: las cuotas
    print("\n--- 💰 CUOTAS DE LA CASA DE APUESTAS ---")
    cuota_l = pedir_numero(f"Cuota para victoria de {local}", float, 2.00)
    cuota_e = pedir_numero("Cuota para el Empate", float, 3.30)
    cuota_v = pedir_numero(f"Cuota para victoria de {visita}", float, 3.50)
    
    # 4. Llamamos al cerebro del AP Engine v1.0 para analizar el partido
    motor = APEngineV1()
    cuotas = {'local': cuota_l, 'empate': cuota_e, 'visita': cuota_v}
    
    resultado_engine = motor.analizar_partido(local, visita, stats_local, stats_visita, cuotas)
    
    # 5. Guardamos todo en SQLite asegurándonos de que la tabla exista
    print("⏳ Guardando partido y predicción en 'ap_engine.db'...")
    crear_base_de_datos()
    conn = sqlite3.connect('data/ap_engine.db')
    cursor = conn.cursor()
    
    try:
        # Insertar el partido
        cursor.execute('''
        INSERT INTO partidos (
            fecha, liga, equipo_local, equipo_visitante,
            goles_prom_local, goles_prom_visita, tiros_prom_local, tiros_prom_visita,
            corners_prom_local, corners_prom_visita, lesiones_clave_local, lesiones_clave_visita
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha, liga, local, visita, *stats_local, *stats_visita))
        
        id_partido_creado = cursor.lastrowid
        
        # Insertar la predicción
        cursor.execute('''
        INSERT INTO historial_predicciones (
            id_partido, version_engine, prob_local, prob_empate, prob_visita,
            cuota_bookie_local, cuota_bookie_empate, cuota_bookie_visita,
            ev_local, apuesta_recomendada, kelly_stake_sugerido
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_partido_creado, 'v1.0_ETL', 
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