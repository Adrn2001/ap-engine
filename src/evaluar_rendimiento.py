import sqlite3
import pandas as pd
from db_setup import crear_base_de_datos

def verificar_y_reparar_db():
    """Garantiza que la carpeta y las tablas existan siempre."""
    crear_base_de_datos()

def mostrar_partidos_pendientes(conn):
    query = '''
    SELECT p.id_partido, p.fecha, p.equipo_local, p.equipo_visitante, h.apuesta_recomendada, h.kelly_stake_sugerido
    FROM partidos p
    JOIN historial_predicciones h ON p.id_partido = h.id_partido
    WHERE p.estatus = 'PENDIENTE'
    '''
    df = pd.read_sql_query(query, conn)
    return df

def registrar_resultado():
    verificar_y_reparar_db()
    conn = sqlite3.connect('data/ap_engine.db')
    
    print("\n" + "="*60)
    print("📝 AP ENGINE 1.0 | REGISTRO DE MARCADORES Y EVALUACIÓN")
    print("="*60)
    
    df_pendientes = mostrar_partidos_pendientes(conn)
    
    if df_pendientes.empty:
        print("ℹ️ No hay partidos pendientes de resultado en la base de datos.")
        print("💡 Tip: Corre primero 'python src/guardar_partido.py' para ingresar un partido.")
        conn.close()
        return

    print("\n--- ⏳ PARTIDOS ESPERANDO MARCADOR FINAL ---")
    for idx, row in df_pendientes.iterrows():
        print(f"ID #{row['id_partido']} | {row['fecha']} | {row['equipo_local']} vs {row['equipo_visitante']} -> Apuesta sugerida: {row['apuesta_recomendada']} (${row['kelly_stake_sugerido']})")
    
    print("-" * 60)
    try:
        id_input = input("\n👉 Ingresa el ID del partido que ya terminó (o presiona Enter para salir): ").strip()
        if not id_input:
            conn.close()
            return
        
        id_p = int(id_input)
        
        # Verificar que el ID exista
        if id_p not in df_pendientes['id_partido'].values:
            print("❌ ID no válido o no está pendiente.")
            conn.close()
            return
            
        row_partido = df_pendientes[df_pendientes['id_partido'] == id_p].iloc[0]
        local_nombre = row_partido['equipo_local']
        visita_nombre = row_partido['equipo_visitante']
        apuesta_sugerida = str(row_partido['apuesta_recomendada'])
        
        goles_l = int(input(f"⚽ Goles reales anotados por {local_nombre}: ").strip())
        goles_v = int(input(f"⚽ Goles reales anotados por {visita_nombre}: ").strip())
        
        # Determinar resultado real del partido
        if goles_l > goles_v:
            resultado_cancha = "LOCAL"
        elif goles_v > goles_l:
            resultado_cancha = "VISITA"
        else:
            resultado_cancha = "EMPATE"
            
        # Evaluar si la apuesta de AP Engine fue ganadora
        if "VICTORIA LOCAL" in apuesta_sugerida and resultado_cancha == "LOCAL":
            res_apuesta = "GANADA"
        elif "VICTORIA VISITANTE" in apuesta_sugerida and resultado_cancha == "VISITA":
            res_apuesta = "GANADA"
        elif "EMPATE" in apuesta_sugerida and resultado_cancha == "EMPATE":
            res_apuesta = "GANADA"
        elif "NINGUNA" in apuesta_sugerida:
            res_apuesta = "NULA (Sin apuesta)"
        else:
            res_apuesta = "PERDIDA"
            
        cursor = conn.cursor()
        
        # 1. Actualizar la tabla partidos con el marcador real
        cursor.execute('''
        UPDATE partidos 
        SET goles_real_local = ?, goles_real_visita = ?, estatus = 'FINALIZADO'
        WHERE id_partido = ?
        ''', (goles_l, goles_v, id_p))
        
        # 2. Actualizar el resultado en el historial de predicciones
        cursor.execute('''
        UPDATE historial_predicciones
        SET resultado_apuesta = ?
        WHERE id_partido = ?
        ''', (res_apuesta, id_p))
        
        conn.commit()
        
        icono = "✅" if res_apuesta == "GANADA" else ("⚪" if "NULA" in res_apuesta else "❌")
        print(f"\n{icono} ¡Partido actualizado! Resultado de la apuesta de AP Engine: {res_apuesta}")
        
    except ValueError:
        print("❌ Por favor ingresa números enteros válidos para los goles y el ID.")
    except Exception as e:
        print(f"❌ Error al actualizar: {e}")
    finally:
        conn.close()
        
    # Mostrar el tablero general de rendimiento
    mostrar_dashboard_roi()

def mostrar_dashboard_roi():
    conn = sqlite3.connect('data/ap_engine.db')
    query = '''
    SELECT cuota_bookie_local, cuota_bookie_empate, cuota_bookie_visita, 
           apuesta_recomendada, kelly_stake_sugerido, resultado_apuesta
    FROM historial_predicciones
    WHERE resultado_apuesta IS NOT NULL AND resultado_apuesta != 'NULA (Sin apuesta)'
    '''
    try:
        df = pd.read_sql_query(query, conn)
    except:
        conn.close()
        return
    conn.close()
    
    print("\n" + "="*60)
    print("📊 TABLERO DE RENDIMIENTO GENERAL (AP ENGINE ROI)")
    print("="*60)
    
    if df.empty:
        print("ℹ️ Aún no hay apuestas evaluadas para calcular el ROI.")
        print("="*60 + "\n")
        return
        
    total_apuestas = len(df)
    ganadas = len(df[df['resultado_apuesta'] == 'GANADA'])
    perdidas = len(df[df['resultado_apuesta'] == 'PERDIDA'])
    tasa_acierto = (ganadas / total_apuestas) * 100
    
    capital_invertido = 0.0
    retorno_total = 0.0
    
    for idx, row in df.iterrows():
        stake = row['kelly_stake_sugerido']
        if stake <= 0:
            continue
        capital_invertido += stake
        
        if row['resultado_apuesta'] == 'GANADA':
            # Determinar qué cuota se pagó
            if "LOCAL" in row['apuesta_recomendada']:
                cuota = row['cuota_bookie_local']
            elif "VISITANTE" in row['apuesta_recomendada']:
                cuota = row['cuota_bookie_visita']
            else:
                cuota = row['cuota_bookie_empate']
            retorno_total += (stake * cuota)
            
    ganancia_neta = retorno_total - capital_invertido
    roi = (ganancia_neta / capital_invertido * 100) if capital_invertido > 0 else 0.0
    
    print(f"🎯 Apuestas Evaluadas: {total_apuestas} | ✅ Ganadas: {ganadas} | ❌ Perdidas: {perdidas}")
    print(f"📈 Tasa de Acierto (Win Rate): {tasa_acierto:.1f}%")
    print("-" * 60)
    print(f"💼 Capital Apostado (Total Stakes): ${capital_invertido:.2f} USD")
    print(f"💵 Retorno Total (Cobrado en Bookies): ${retorno_total:.2f} USD")
    
    color_roi = "🟢" if roi >= 0 else "🔴"
    print(f"{color_roi} Ganancia/Pérdida Neta: ${ganancia_neta:+.2f} USD")
    print(f"🚀 ROI del Motor: {roi:+.2f}%")
    print("="*60 + "\n")

if __name__ == '__main__':
    registrar_resultado()