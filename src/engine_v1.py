import sqlite3
import numpy as np
import pandas as pd
import math
import os
from modulo_elo import SistemaElo

class APEngineV1:
    """
    Cerebro de Predicción Deportiva - AP ENGINE 2.0 
    (Arquitectura: Dixon-Coles Bivariado + xG Híbrido + Memoria Elo)
    """
    def __init__(self, db_path='data/ap_engine.db'):
        self.db_path = db_path
        self.elo_sys = SistemaElo(db_path)
        # Parámetro Rho (ρ) de Dixon-Coles para fútbol (-0.13 es el estándar empírico)
        self.rho = -0.13 

    def calcular_factor_elo(self, elo_local, elo_visita):
        """Modulador suave de xG basado en la diferencia histórica de puntos Elo."""
        dif_elo = (elo_local + self.elo_sys.ventaja_local) - elo_visita
        ajuste_l = 1.0 + (dif_elo / 100.0) * 0.05
        ajuste_v = 1.0 - (dif_elo / 100.0) * 0.05
        return round(max(0.75, min(1.25, ajuste_l)), 3), round(max(0.75, min(1.25, ajuste_v)), 3)

    def calcular_xg_ajustado(self, goles_prom, tiros_prom, corners_prom, lesiones, factor_elo):
        """Calcula la Esperanza de Gol (xG Híbrido 2.0)."""
        ajuste_volumen = 1.0 + ((tiros_prom - 4.5) * 0.03) + ((corners_prom - 5.0) * 0.01)
        penalizacion_lesiones = max(0.5, 1.0 - (lesiones * 0.08))
        xg_ajustado = goles_prom * ajuste_volumen * penalizacion_lesiones * factor_elo
        return max(0.1, xg_ajustado)

    def _poisson_pmf(self, k, lam):
        """Fórmula matemática de la masa de probabilidad de Poisson pura."""
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    def _ajuste_dixon_coles(self, x, y, lam_l, lam_v):
        """
        Fórmula de corrección de covarianza de Dixon y Coles (1997).
        Reajusta matemáticamente la probabilidad de marcadores (0,0), (1,0), (0,1) y (1,1).
        """
        if x == 0 and y == 0:
            return 1.0 - (lam_l * lam_v * self.rho)
        elif x == 0 and y == 1:
            return 1.0 + (lam_l * self.rho)
        elif x == 1 and y == 0:
            return 1.0 + (lam_v * self.rho)
        elif x == 1 and y == 1:
            return 1.0 - self.rho
        else:
            return 1.0

    def calcular_probabilidades_dixon_coles(self, xg_local, xg_visita, max_goles=10):
        """
        Genera una matriz bivariada de marcadores (0-0 hasta 10-10) aplicando
        la corrección de Dixon-Coles y extrae las probabilidades exactas del mercado 1X2.
        """
        matriz_prob = np.zeros((max_goles, max_goles))
        
        # 1. Llenamos la matriz marcador por marcador
        for x in range(max_goles):
            for y in range(max_goles):
                p_poisson = self._poisson_pmf(x, xg_local) * self._poisson_pmf(y, xg_visita)
                factor_dc = self._ajuste_dixon_coles(x, y, xg_local, xg_visita)
                matriz_prob[x, y] = max(0.0, p_poisson * factor_dc)
                
        # 2. Normalizamos la matriz para que la suma exacta sea 100%
        matriz_prob /= np.sum(matriz_prob)
        
        # 3. Extraemos probabilidades sumando triángulos y diagonal de la matriz
        # tril(-1) = Gana Local (goles_l > goles_v)
        p_local = np.sum(np.tril(matriz_prob, -1)) * 100
        # diag(0)  = Empate (goles_l == goles_v)
        p_empate = np.sum(np.diag(matriz_prob)) * 100
        # triu(1)  = Gana Visita (goles_l < goles_v)
        p_visita = np.sum(np.triu(matriz_prob, 1)) * 100
        
        # Extraemos también la probabilidad de Over/Under 2.5 goles desde la misma matriz
        p_over_goles = 0.0
        for x in range(max_goles):
            for y in range(max_goles):
                if (x + y) > 2.5:
                    p_over_goles += matriz_prob[x, y] * 100
        p_under_goles = 100.0 - p_over_goles
        
        return {
            '1X2': (round(p_local, 2), round(p_empate, 2), round(p_visita, 2)),
            'goles_25': (round(p_over_goles, 2), round(p_under_goles, 2)),
            'matriz': matriz_prob # Guardamos la matriz por si queremos ver marcadores exactos
        }

    def simular_corners_poisson(self, corners_l, corners_v, sims=10000):
        """Los córners se mantienen por Monte Carlo - Poisson independiente."""
        c_l = np.random.poisson(max(1.0, corners_l), sims)
        c_v = np.random.poisson(max(1.0, corners_v), sims)
        total = c_l + c_v
        p_ov = np.mean(total > 9.5) * 100
        return round(p_ov, 2), round(100.0 - p_ov, 2)

    def evaluar_valor_y_kelly(self, prob_engine, cuota_bookie, bankroll=1000, kelly_fraction=0.5):
        """Calcula el Valor Esperado (EV) y el tamaño de apuesta Kelly."""
        if cuota_bookie <= 1.0:
            return 0.0, "SIN CUOTA", 0.0
            
        prob_decimal = prob_engine / 100.0
        ev = (prob_decimal * cuota_bookie) - 1.0
        
        if ev <= 0:
            return round(ev * 100, 2), "SIN VALOR", 0.0
            
        b = cuota_bookie - 1.0
        q = 1.0 - prob_decimal
        kelly_pct = ((b * prob_decimal) - q) / b
        
        kelly_ajustado = max(0.0, kelly_pct * kelly_fraction)
        stake_dolares = round(bankroll * kelly_ajustado, 2)
        
        return round(ev * 100, 2), f"¡VALOR! ({round(kelly_ajustado*100, 1)}% Bank)", stake_dolares

    def analizar_partido(self, local, visita, stats_local, stats_visita, cuotas):
        """Función principal V2.0: Dixon-Coles + xG + Elo."""
        elo_l = self.elo_sys.obtener_elo(local)
        elo_v = self.elo_sys.obtener_elo(visita)
        factor_elo_l, factor_elo_v = self.calcular_factor_elo(elo_l, elo_v)
        
        xg_local = self.calcular_xg_ajustado(*stats_local, factor_elo=factor_elo_l)
        xg_visita = self.calcular_xg_ajustado(*stats_visita, factor_elo=factor_elo_v)
        
        # 1. Calculamos probabilidades 1X2 y Goles con el Modelo Dixon-Coles
        dc = self.calcular_probabilidades_dixon_coles(xg_local, xg_visita)
        p_l, p_e, p_v = dc['1X2']
        p_ov_g, p_un_g = dc['goles_25']
        
        # 2. Córners por simulación de Poisson
        p_ov_c, p_un_c = self.simular_corners_poisson(stats_local[2], stats_visita[2])
        
        # 3. Evaluación de cuotas
        ev_l, _, stake_l = self.evaluar_valor_y_kelly(p_l, cuotas.get('local', 0))
        ev_e, _, stake_e = self.evaluar_valor_y_kelly(p_e, cuotas.get('empate', 0))
        ev_v, _, stake_v = self.evaluar_valor_y_kelly(p_v, cuotas.get('visita', 0))
        
        ev_ov_g, _, stake_ov_g = self.evaluar_valor_y_kelly(p_ov_g, cuotas.get('over_25', 0))
        ev_un_g, _, stake_un_g = self.evaluar_valor_y_kelly(p_un_g, cuotas.get('under_25', 0))
        
        ev_ov_c, _, stake_ov_c = self.evaluar_valor_y_kelly(p_ov_c, cuotas.get('over_corners', 0))
        ev_un_c, _, stake_un_c = self.evaluar_valor_y_kelly(p_un_c, cuotas.get('under_corners', 0))
        
        catalogo_apuestas = [
            {"mercado": f"VICTORIA LOCAL ({local})", "prob": p_l, "cuota": cuotas.get('local', 0), "ev": ev_l, "stake": stake_l},
            {"mercado": "EMPATE (Ajuste Dixon-Coles)", "prob": p_e, "cuota": cuotas.get('empate', 0), "ev": ev_e, "stake": stake_e},
            {"mercado": f"VICTORIA VISITANTE ({visita})", "prob": p_v, "cuota": cuotas.get('visita', 0), "ev": ev_v, "stake": stake_v},
            {"mercado": "OVER 2.5 GOLES", "prob": p_ov_g, "cuota": cuotas.get('over_25', 0), "ev": ev_ov_g, "stake": stake_ov_g},
            {"mercado": "UNDER 2.5 GOLES", "prob": p_un_g, "cuota": cuotas.get('under_25', 0), "ev": ev_un_g, "stake": stake_un_g},
            {"mercado": "OVER 9.5 CÓRNERS", "prob": p_ov_c, "cuota": cuotas.get('over_corners', 0), "ev": ev_ov_c, "stake": stake_ov_c},
            {"mercado": "UNDER 9.5 CÓRNERS", "prob": p_un_c, "cuota": cuotas.get('under_corners', 0), "ev": ev_un_c, "stake": stake_un_c}
        ]
        
        catalogo_apuestas.sort(key=lambda x: x['ev'], reverse=True)
        mejor_pick = catalogo_apuestas[0]
        
        print("\n" + "="*65)
        print(f"🧬 AP ENGINE 2.0 | MODELO DIXON-COLES + ELO HISTÓRICO")
        print("="*65)
        print(f"Encuentro: {local} vs {visita}")
        print(f"🏅 Ranking Elo: {local} ({elo_l:.1f} pts) vs {visita} ({elo_v:.1f} pts)")
        print(f"⚽ xG Híbrido 2.0: {local} ({xg_local:.2f}) - {visita} ({xg_visita:.2f})")
        print("-" * 65)
        print(f"📊 PROBABILIDADES EXACTAS (MATRIZ DIXON-COLES):")
        print(f"   [1X2] 🏠 {local}: {p_l}% (EV: {ev_l:+.1f}%) | 🤝 Empate: {p_e}% | ✈️ {visita}: {p_v}%")
        print(f"   [Goles] ⚽ Over 2.5: {p_ov_g}% | Under 2.5: {p_un_g}%")
        print(f"   [Córners] 🚩 Over 9.5: {p_ov_c}% (EV: {ev_ov_c:+.1f}%) | Under 9.5: {p_un_c}%")
        print("-" * 65)
        
        if mejor_pick['ev'] > 0:
            apuesta_sugerida = f"{mejor_pick['mercado']} @ {mejor_pick['cuota']}"
            stake_final = mejor_pick['stake']
            print(f"🎯 MEJOR APUESTA CON VALOR (EV+): {apuesta_sugerida}")
            print(f"🔥 Edge de ganancia (V2.0): +{mejor_pick['ev']:.2f}%")
            print(f"💰 Stake Sugerido (Medio Kelly): ${stake_final} USD")
        else:
            apuesta_sugerida = "NINGUNA (Mercado eficiente, sin valor)"
            stake_final = 0.0
            print(f"🛡️ DECISIÓN DEL MOTOR: {apuesta_sugerida}")
            print(f"💡 El mercado absorbió la fuerza de ambos equipos. Preservar bankroll.")
        print("="*65 + "\n")
        
        return {
            'prob_local': p_l, 'prob_empate': p_e, 'prob_visita': p_v,
            'prob_over_25': p_ov_g, 'prob_over_corners': p_ov_c,
            'ev_local': ev_l, 'apuesta': apuesta_sugerida, 'stake': stake_final
        }

# =====================================================================
# PRUEBA EN VIVO: DIXON-COLES EN ACCIÓN
# =====================================================================
if __name__ == '__main__':
    motor = APEngineV1() # Corriendo con arquitectura v2.0
    
    stats_l = (1.6, 5.0, 5.5, 0) # (goles, tiros, córners, lesiones)
    stats_v = (1.1, 3.5, 4.0, 0)
    
    # Cuotas con el empate pagando 3.40
    cuotas = {
        'local': 1.90, 'empate': 3.40, 'visita': 4.20,
        'over_25': 2.10, 'under_25': 1.75,
        'over_corners': 1.95, 'under_corners': 1.85
    }
    
    motor.analizar_partido("Liga de Quito", "Emelec", stats_l, stats_v, cuotas)