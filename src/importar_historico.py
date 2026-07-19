import sqlite3
import pandas as pd
import sys
import io
from datetime import datetime
from db_setup import crear_base_de_datos
from modulo_elo import SistemaElo

def descargar_e_importar_temporadas():
    print("\n" + "="*65)
    print("🛸 AP ENGINE | INYECTOR MASIVO DE DATOS HISTÓRICOS (ETL)")
    print("="*65)
    
    # 1. Asegurar que la base y tablas existan
    crear_base_de_datos()
    elo_sys = SistemaElo()
    
    fuentes_csv = {
        "Premier League (Inglaterra)": "https://www.football-data.co.uk/mmz4281/2324/E0.csv",
        "La Liga (España)": "https://www.football-data.co.uk/mmz4281/2324/SP1.csv"
    }
    
    total_insertados = 0
    
    for torneo, url in fuentes_csv.items():
        print(f"⏳ Descargando base de datos oficial de: {torneo}...")
        try:
            df = pd.read_csv(url)
            df = df.dropna(subset=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'])
            
            print(f"📊 Procesando y calibrando {len(df)} partidos reales de {torneo}...")
            
            for idx, row in df.iterrows():
                local = str(row['HomeTeam']).strip()
                visita = str(row['AwayTeam']).strip()
                goles_l = int(row['FTHG'])
                goles_v = int(row['FTAG'])
                
                tiros_l = float(row['HST']) if 'HST' in row and pd.notna(row['HST']) else 4.5
                tiros_v = float(row['AST']) if 'AST' in row and pd.notna(row['AST']) else 3.8
                corners_l = float(row['HC']) if 'HC' in row and pd.notna(row['HC']) else 5.0
                corners_v = float(row['AC']) if 'AC' in row and pd.notna(row['AC']) else 4.0
                
                fecha_str = str(row['Date'])
                
                # A) ABRIR, INSERTAR, GUARDAR Y CERRAR AL INSTANTE (Evita el bloqueo 'database is locked')
                # Agregamos timeout=10.0 como escudo adicional de concurrencia
                conn = sqlite3.connect('data/ap_engine.db', timeout=10.0)
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO partidos (
                    fecha, liga, equipo_local, equipo_visitante,
                    goles_prom_local, goles_prom_visita, tiros_prom_local, tiros_prom_visita,
                    corners_prom_local, corners_prom_visita, lesiones_clave_local, lesiones_clave_visita,
                    goles_real_local, goles_real_visita, estatus
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, 'FINALIZADO')
                ''', (fecha_str, torneo, local, visita, goles_l, goles_v, tiros_l, tiros_v, corners_l, corners_v, goles_l, goles_v))
                conn.commit()
                conn.close() # Conexión cerrada y archivo liberado al 100%
                
                total_insertados += 1
                
                # B) Calibrar Elo silenciando la consola temporalmente para máxima velocidad
                stdout_original = sys.stdout
                sys.stdout = io.StringIO() # Desviamos los prints a la memoria invisible
                elo_sys.procesar_partido(local, visita, goles_l, goles_v)
                sys.stdout = stdout_original # Devolvemos la consola a la normalidad
                
            print(f"✅ ¡{torneo} importado y calibrado sin errores!")
            
        except Exception as e:
            print(f"❌ Error al descargar o procesar {torneo}: {e}")
            
    print("-" * 65)
    print(f"🚀 INYECCIÓN FINALIZADA: Se cargaron {total_insertados} partidos históricos reales en SQLite.")
    print("🏆 Tu base de datos y tu Ranking Elo ahora están calibrados a nivel profesional.")
    print("="*65 + "\n")

if __name__ == '__main__':
    descargar_e_importar_temporadas()