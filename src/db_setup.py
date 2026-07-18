import sqlite3
import os

def crear_base_de_datos():
    """Crea la carpeta data/ y las tablas relacionales si no existen."""
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect('data/ap_engine.db')
    cursor = conn.cursor()

    # Tabla de Partidos (Entradas)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS partidos (
        id_partido INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        liga TEXT NOT NULL,
        equipo_local TEXT NOT NULL,
        equipo_visitante TEXT NOT NULL,
        goles_prom_local REAL,
        goles_prom_visita REAL,
        tiros_prom_local REAL,
        tiros_prom_visita REAL,
        corners_prom_local REAL,
        corners_prom_visita REAL,
        lesiones_clave_local INTEGER DEFAULT 0,
        lesiones_clave_visita INTEGER DEFAULT 0,
        goles_real_local INTEGER NULL,
        goles_real_visita INTEGER NULL,
        estatus TEXT DEFAULT 'PENDIENTE'
    )
    ''')

    # Tabla de Predicciones y Apuestas (Salidas)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historial_predicciones (
        id_prediccion INTEGER PRIMARY KEY AUTOINCREMENT,
        id_partido INTEGER,
        version_engine TEXT NOT NULL,
        prob_local REAL NOT NULL,
        prob_empate REAL NOT NULL,
        prob_visita REAL NOT NULL,
        cuota_bookie_local REAL,
        cuota_bookie_empate REAL,
        cuota_bookie_visita REAL,
        ev_local REAL,
        apuesta_recomendada TEXT,
        kelly_stake_sugerido REAL DEFAULT 0,
        resultado_apuesta TEXT NULL,
        FOREIGN KEY (id_partido) REFERENCES partidos (id_partido)
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    crear_base_de_datos()
    print("¡Base de datos y tablas verificadas con éxito!")