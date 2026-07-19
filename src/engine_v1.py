import sqlite3
import numpy as np
import pandas as pd
import os

class APEngineV1:
    def __init__(self, db_path='data/ap_engine.db'):
        self.db_path = db_path

    def calcular_xg_ajustado(self, goles_prom, tiros_prom, corners_prom, lesiones):
        """Calcula el xG ajustado por peligro y lesiones clave."""
        ajuste_volumen = 1.0 + ((tiros_prom - 4.5) * 0.03) + ((corners_prom - 5.0) * 0.01)
        penalizacion_lesiones = max(0.5, 1.0 - (lesiones * 0.08))
        xg_ajustado = goles_prom * ajuste_volumen * penalizacion_lesiones
        return max(0.1, xg_ajustado)

    def simular_partido_completo(self, xg_local, xg_visita, corners_prom_l, corners_prom_v, simulaciones=10000):
        """
        Simula N partidos usando la distribución de Poisson para calcular:
        - Mercado 1X2 (Local, Empate, Visita)
        - Mercado de Goles (Over/Under 2.5)
        - Mercado de Córners (Over/Under 9.5)
        """
        # 1. Simulación de Goles
        goles_l = np.random.poisson(xg_local, simulaciones)
        goles_v = np.random.poisson(xg_visita, simulaciones)
        total_goles = goles_l + goles_v
        
        p_l = np.mean(goles_l > goles_v) * 100
        p_e = np.mean(goles_l == goles_v) * 100
        p_v = np.mean(goles_l < goles_v) * 100
        
        p_over_goles = np.mean(total_goles > 2.5) * 100
        p_under_goles = np.mean(total_goles < 2.5) * 100
        
        # 2. Simulación de Córners
        corners_l = np.random.poisson(max(1.0, corners_prom_l), simulaciones)
        corners_v = np.random.poisson(max(1.0, corners_prom_v), simulaciones)
        total_corners = corners_l + corners_v
        
        p_over_corners = np.mean(total_corners > 9.5) * 100
        p_under_corners = np.mean(total_corners < 9.5) * 100
        
        return {
            '1X2': (round(p_l, 2), round(p_e, 2), round(p_v, 2)),
            'goles_25': (round(p_over_goles, 2), round(p_under_goles, 2)),
            'corners_95': (round(p_over_corners, 2), round(p_under_corners, 2))
        }

    def evaluar_valor_y_kelly(self, prob_engine, cuota_bookie, bankroll=1000, kelly_fraction=0.5):
        """Calcula el Valor Esperado (EV) y el tamaño de apuesta sugerido."""
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
        """Procesa el partido y escanea TODOS los mercados en búsqueda de valor."""
        xg_local = self.calcular_xg_ajustado(*stats_local)
        xg_visita = self.calcular_xg_ajustado(*stats_visita)
        
        # stats_local = (goles, tiros, corners, lesiones) -> el índice [2] son los córners
        sim = self.simular_partido_completo(xg_local, xg_visita, stats_local[2], stats_visita[2])
        
        # Evaluar Mercado 1X2
        p_l, p_e, p_v = sim['1X2']
        ev_l, _, stake_l = self.evaluar_valor_y_kelly(p_l, cuotas.get('local', 0))
        ev_e, _, stake_e = self.evaluar_valor_y_kelly(p_e, cuotas.get('empate', 0))
        ev_v, _, stake_v = self.evaluar_valor_y_kelly(p_v, cuotas.get('visita', 0))
        
        # Evaluar Mercado Goles Over/Under 2.5
        p_ov_g, p_un_g = sim['goles_25']
        ev_ov_g, _, stake_ov_g = self.evaluar_valor_y_kelly(p_ov_g, cuotas.get('over_25', 0))
        ev_un_g, _, stake_un_g = self.evaluar_valor_y_kelly(p_un_g, cuotas.get('under_25', 0))
        
        # Evaluar Mercado Córners Over/Under 9.5
        p_ov_c, p_un_c = sim['corners_95']
        ev_ov_c, _, stake_ov_c = self.evaluar_valor_y_kelly(p_ov_c, cuotas.get('over_corners', 0))
        ev_un_c, _, stake_un_c = self.evaluar_valor_y_kelly(p_un_c, cuotas.get('under_corners', 0))
        
        # Armar el catálogo completo de apuestas analizadas para encontrar la #1
        catalogo_apuestas = [
            {"mercado": f"VICTORIA LOCAL ({local})", "prob": p_l, "cuota": cuotas.get('local', 0), "ev": ev_l, "stake": stake_l},
            {"mercado": "EMPATE", "prob": p_e, "cuota": cuotas.get('empate', 0), "ev": ev_e, "stake": stake_e},
            {"mercado": f"VICTORIA VISITANTE ({visita})", "prob": p_v, "cuota": cuotas.get('visita', 0), "ev": ev_v, "stake": stake_v},
            {"mercado": "OVER 2.5 GOLES", "prob": p_ov_g, "cuota": cuotas.get('over_25', 0), "ev": ev_ov_g, "stake": stake_ov_g},
            {"mercado": "UNDER 2.5 GOLES", "prob": p_un_g, "cuota": cuotas.get('under_25', 0), "ev": ev_un_g, "stake": stake_un_g},
            {"mercado": "OVER 9.5 CÓRNERS", "prob": p_ov_c, "cuota": cuotas.get('over_corners', 0), "ev": ev_ov_c, "stake": stake_ov_c},
            {"mercado": "UNDER 9.5 CÓRNERS", "prob": p_un_c, "cuota": cuotas.get('under_corners', 0), "ev": ev_un_c, "stake": stake_un_c}
        ]
        
        # Ordenar por el mayor Valor Esperado (EV)
        catalogo_apuestas.sort(key=lambda x: x['ev'], reverse=True)
        mejor_pick = catalogo_apuestas[0]
        
        print("\n" + "="*60)
        print(f"⚽ AP ENGINE 1.0 | ANÁLISIS MULTI-MERCADO")
        print("="*60)
        print(f"Encuentro: {local} vs {visita}")
        print(f"xG Estimado: {local} ({xg_local:.2f}) - {visita} ({xg_visita:.2f})")
        print("-" * 60)
        print(f"📊 PROBABILIDADES Y ESCANEO DE MERCADOS:")
        print(f"   [1X2] 🏠 {local}: {p_l}% (EV: {ev_l:+.1f}%) | 🤝 Empate: {p_e}% | ✈️ {visita}: {p_v}%")
        print(f"   [Goles] ⚽ Over 2.5: {p_ov_g}% (EV: {ev_ov_g:+.1f}%) | Under 2.5: {p_un_g}%")
        print(f"   [Córners] 🚩 Over 9.5: {p_ov_c}% (EV: {ev_ov_c:+.1f}%) | Under 9.5: {p_un_c}%")
        print("-" * 60)
        
        if mejor_pick['ev'] > 0:
            apuesta_sugerida = f"{mejor_pick['mercado']} @ {mejor_pick['cuota']}"
            stake_final = mejor_pick['stake']
            print(f"🎯 MEJOR APUESTA CON VALOR (EV+): {apuesta_sugerida}")
            print(f"🔥 Edge de ganancia a largo plazo: +{mejor_pick['ev']:.2f}%")
            print(f"💰 Stake Sugerido (Medio Kelly): ${stake_final} USD")
        else:
            apuesta_sugerida = "NINGUNA (No se encontró valor en ningún mercado)"
            stake_final = 0.0
            print(f"🛡️ DECISIÓN DEL MOTOR: {apuesta_sugerida}")
            print(f"💡 El mercado está bien ajustado por la casa. Preservar bankroll.")
        print("="*60 + "\n")
        
        return {
            'prob_local': p_l, 'prob_empate': p_e, 'prob_visita': p_v,
            'prob_over_25': p_ov_g, 'prob_over_corners': p_ov_c,
            'ev_local': ev_l, 'apuesta': apuesta_sugerida, 'stake': stake_final
        }

# =====================================================================
# PRUEBA RÁPIDA DE LOS NUEVOS MERCADOS
# =====================================================================
if __name__ == '__main__':
    motor = APEngineV1()
    
    # Equipo A muy ofensivo vs Equipo B débil (partido abierto, ideal para Over de Goles)
    stats_l = (2.4, 7.0, 6.5, 0) # (goles, tiros, córners, lesiones)
    stats_v = (1.5, 4.5, 5.0, 1)
    
    cuotas_multi_mercado = {
        'local': 1.60, 'empate': 4.00, 'visita': 5.50,
        'over_25': 1.95,  # Cuota por más de 2.5 goles
        'under_25': 1.85, # Cuota por menos de 2.5 goles
        'over_corners': 2.10, # Cuota por más de 9.5 córners
        'under_corners': 1.70
    }
    
    motor.analizar_partido("Barcelona SC", "Emelec", stats_l, stats_v, cuotas_multi_mercado)