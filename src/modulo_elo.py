import sqlite3
from datetime import datetime

class SistemaElo:
    """
    Módulo de Puntuación Elo Dinámico para AP Engine 2.0.
    Calcula probabilidades basadas en fuerza histórica y actualiza puntajes tras cada partido.
    """
    def __init__(self, db_path='data/ap_engine.db'):
        self.db_path = db_path
        self.elo_inicial = 1500.0  # Puntaje base para cualquier equipo nuevo
        self.k_base = 20.0         # Factor de volatilidad (qué tan rápido sube/baja el puntaje)
        self.ventaja_local = 100.0 # Puntos extra temporales por jugar en casa

    def obtener_elo(self, equipo):
        """Busca el Elo actual de un equipo en la BD. Si no existe, lo crea con 1500."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT puntuacion_elo FROM ranking_elo WHERE equipo = ?", (equipo.strip().lower(),))
        resultado = cursor.fetchone()
        
        if resultado:
            elo = resultado[0]
        else:
            # Si el equipo es nuevo en la base, lo insertamos con 1500
            elo = self.elo_inicial
            cursor.execute('''
            INSERT INTO ranking_elo (equipo, puntuacion_elo, partidos_jugados, ultima_actualizacion)
            VALUES (?, ?, 0, ?)
            ''', (equipo.strip().lower(), self.elo_inicial, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            
        conn.close()
        return elo

    def calcular_expectativa_victoria(self, elo_local, elo_visita):
        """
        Fórmula matemática de expectativa Elo:
        Devuelve un valor entre 0 y 1 que representa la probabilidad estimada de ganar.
        """
        # Sumamos la ventaja de local al equipo de casa
        elo_local_ajustado = elo_local + self.ventaja_local
        
        # Fórmula logística de probabilidad de Elo
        expectativa_local = 1.0 / (1.0 + 10.0 ** ((elo_visita - elo_local_ajustado) / 400.0))
        expectativa_visita = 1.0 - expectativa_local
        
        return expectativa_local, expectativa_visita

    def calcular_multiplicador_goles(self, dif_goles):
        """
        Si un equipo gana por goleada (ej. 3-0 o 4-1), el ranking debe moverse más agresivamente.
        """
        if dif_goles <= 1:
            return 1.0
        elif dif_goles == 2:
            return 1.5
        else:
            # Fórmula de rendimiento por margen contundente
            return (11.0 + dif_goles) / 8.0

    def procesar_partido(self, equipo_local, equipo_visita, goles_local, goles_visita):
        """
        Toma el resultado real de un partido, calcula el nuevo Elo para ambos
        y lo guarda inmediatamente en SQLite.
        """
        elo_l = self.obtener_elo(equipo_local)
        elo_v = self.obtener_elo(equipo_visita)
        
        exp_l, exp_v = self.calcular_expectativa_victoria(elo_l, elo_v)
        
        # Definir resultado numérico (1 = gana local, 0.5 = empate, 0 = gana visita)
        if goles_local > goles_visita:
            res_l, res_v = 1.0, 0.0
        elif goles_local == goles_visita:
            res_l, res_v = 0.5, 0.5
        else:
            res_l, res_v = 0.0, 1.0
            
        # Calcular K ajustado por la diferencia de goles
        dif_goles = abs(goles_local - goles_visita)
        k_ajustado = self.k_base * self.calcular_multiplicador_goles(dif_goles)
        
        # Fórmulas de actualización de Elo: Nuevo = Viejo + K * (Resultado_Real - Resultado_Esperado)
        nuevo_elo_l = round(elo_l + k_ajustado * (res_l - exp_l), 1)
        nuevo_elo_v = round(elo_v + k_ajustado * (res_v - exp_v), 1)
        
        # Guardar en Base de Datos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute('''
        UPDATE ranking_elo 
        SET puntuacion_elo = ?, partidos_jugados = partidos_jugados + 1, ultima_actualizacion = ?
        WHERE equipo = ?
        ''', (nuevo_elo_l, fecha_hoy, equipo_local.strip().lower()))
        
        cursor.execute('''
        UPDATE ranking_elo 
        SET puntuacion_elo = ?, partidos_jugados = partidos_jugados + 1, ultima_actualizacion = ?
        WHERE equipo = ?
        ''', (nuevo_elo_v, fecha_hoy, equipo_visita.strip().lower()))
        
        conn.commit()
        conn.close()
        
        # Reporte por consola
        cambio_l = nuevo_elo_l - elo_l
        cambio_v = nuevo_elo_v - elo_v
        
        print("\n" + "="*60)
        print("📈 AP ENGINE 2.0 | ACTUALIZACIÓN DE RANKING ELO")
        print("="*60)
        print(f"Marcador Final: {equipo_local} ({goles_local}) vs ({goles_visita}) {equipo_visita}")
        print("-" * 60)
        print(f"🏠 {equipo_local}: {elo_l:.1f} ➔ {nuevo_elo_l:.1f} ({cambio_l:+.1f} pts)")
        print(f"✈️ {equipo_visita}: {elo_v:.1f} ➔ {nuevo_elo_v:.1f} ({cambio_v:+.1f} pts)")
        print("="*60 + "\n")
        
        return nuevo_elo_l, nuevo_elo_v

# =====================================================================
# PRUEBA RÁPIDA DE ELO EN VIVO
# =====================================================================
if __name__ == '__main__':
    elo = SistemaElo()
    
    # 1. Veamos cómo la probabilidad cambia si juegan dos equipos de 1500 (con ventaja local)
    p_local, p_visita = elo.calcular_expectativa_victoria(1500, 1500)
    print(f"⚙️ Probabilidad previa entre equipos iguales -> Local: {p_local*100:.1f}% | Visita: {p_visita*100:.1f}%")
    
    # 2. Simulamos que Barcelona SC golea 3-0 a Emelec en el clásico
    elo.procesar_partido("Barcelona SC", "Emelec", goles_local=3, goles_visita=0)
    
    # 3. Y simulamos otra jornada donde Emelec da el golpe de visita 1-2 contra Liga de Quito
    elo.procesar_partido("Liga de Quito", "Emelec", goles_local=1, goles_visita=2)