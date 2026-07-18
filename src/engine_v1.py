import sqlite3
import numpy as np
import pandas as pd
import os

class APEngineV1:
    def __init__(self, db_path='data/ap_engine.db'):
        self.db_path = db_path

    def calcular_xg_ajustado(self, goles_prom, tiros_prom, corners_prom, lesiones):
        """
        Calcula una esperanza de gol (xG simplificado) ajustando los goles por 
        la generación de peligro (tiros y córners) y penalizando por lesiones clave.
        """
        # 1. Factor de volumen de ataque: 
        # Si un equipo promedia más de 4.5 tiros o 5 córners, su xG sube un poco.
        ajuste_volumen = 1.0 + ((tiros_prom - 4.5) * 0.03) + ((corners_prom - 5.0) * 0.01)
        
        # 2. Penalización por lesiones clave (cada lesión clave reduce 8% la capacidad goleadora)
        penalizacion_lesiones = max(0.5, 1.0 - (lesiones * 0.08))
        
        # xG final ajustado
        xg_ajustado = goles_prom * ajuste_volumen * penalizacion_lesiones
        return max(0.1, xg_ajustado) # Evitar que sea 0 o negativo

    def simular_poisson(self, xg_local, xg_visita, simulaciones=10000):
        """
        Simula N partidos usando la distribución de Poisson para obtener las probabilidades reales.
        """
        # Simulación de marcadores aleatorios basados en Poisson
        goles_local = np.random.poisson(xg_local, simulaciones)
        goles_visita = np.random.poisson(xg_visita, simulaciones)
        
        # Contar resultados y convertir a probabilidad (%)
        prob_local = np.mean(goles_local > goles_visita) * 100
        prob_empate = np.mean(goles_local == goles_visita) * 100
        prob_visita = np.mean(goles_local < goles_visita) * 100
        
        return round(prob_local, 2), round(prob_empate, 2), round(prob_visita, 2)

    def evaluar_valor_y_kelly(self, prob_engine, cuota_bookie, bankroll=1000, kelly_fraction=0.5):
        """
        Calcula el Valor Esperado (EV) y el tamaño de apuesta sugerido con Criterio de Kelly.
        """
        if cuota_bookie <= 1.0:
            return 0, "SIN CUOTA", 0.0
            
        prob_decimal = prob_engine / 100.0
        
        # Valor Esperado: EV = (Probabilidad * Cuota) - 1
        ev = (prob_decimal * cuota_bookie) - 1.0
        
        if ev <= 0:
            return round(ev * 100, 2), "SIN VALOR", 0.0
            
        # Fórmula de Kelly: f = (bp - q) / b  donde b = cuota - 1, p = prob, q = 1 - prob
        b = cuota_bookie - 1.0
        q = 1.0 - prob_decimal
        kelly_pct = ((b * prob_decimal) - q) / b
        
        # Aplicar fracción de Kelly (por gestión de riesgo) y calcular monto del bankroll
        kelly_ajustado = max(0.0, kelly_pct * kelly_fraction)
        stake_dolares = round(bankroll * kelly_ajustado, 2)
        
        return round(ev * 100, 2), f"¡VALOR! ({round(kelly_ajustado*100, 1)}% Bankroll)", stake_dolares

    def analizar_partido(self, local, visita, stats_local, stats_visita, cuotas):
        """
        Función principal: Procesa el partido, genera el pronóstico y busca valor.
        """
        # 1. Calcular xG Ajustado para ambos equipos
        xg_local = self.calcular_xg_ajustado(*stats_local)
        xg_visita = self.calcular_xg_ajustado(*stats_visita)
        
        # 2. Simular probabilidades con Poisson
        p_l, p_e, p_v = self.simular_poisson(xg_local, xg_visita)
        
        # 3. Evaluar apuestas de valor contra las cuotas del bookie
        ev_l, rec_l, stake_l = self.evaluar_valor_y_kelly(p_l, cuotas['local'])
        ev_e, rec_e, stake_e = self.evaluar_valor_y_kelly(p_e, cuotas['empate'])
        ev_v, rec_v, stake_v = self.evaluar_valor_y_kelly(p_v, cuotas['visita'])
        
        # Determinar cuál es la apuesta recomendada del partido
        mejor_ev = max(ev_l, ev_e, ev_v)
        if mejor_ev <= 0:
            apuesta_sugerida = "NINGUNA (No hay valor esperado positivo)"
            stake_final = 0.0
        elif mejor_ev == ev_l:
            apuesta_sugerida = f"VICTORIA LOCAL ({local}) - Cuota {cuotas['local']}"
            stake_final = stake_l
        elif mejor_ev == ev_v:
            apuesta_sugerida = f"VICTORIA VISITANTE ({visita}) - Cuota {cuotas['visita']}"
            stake_final = stake_v
        else:
            apuesta_sugerida = f"EMPATE - Cuota {cuotas['empate']}"
            stake_final = stake_e
            
        print("\n" + "="*50)
        print(f"⚽ AP ENGINE 1.0 | ANÁLISIS DE PARTIDO")
        print("="*50)
        print(f"Encuentro: {local} vs {visita}")
        print(f"xG Estimado (Engine): {local} ({xg_local:.2f}) - {visita} ({xg_visita:.2f})")
        print("-" * 50)
        print(f"PROBABILIDADES AP ENGINE:")
        print(f"🏠 {local}: {p_l}% (Bookie paga: {cuotas['local']}) | EV: {ev_l}%")
        print(f"🤝 Empate: {p_e}% (Bookie paga: {cuotas['empate']}) | EV: {ev_e}%")
        print(f"✈️ {visita}: {p_v}% (Bookie paga: {cuotas['visita']}) | EV: {ev_v}%")
        print("-" * 50)
        print(f"🎯 DECISIÓN DEL MOTOR: {apuesta_sugerida}")
        if stake_final > 0:
            print(f"💰 Tamaño de Apuesta Sugerida (Medio Kelly): ${stake_final} USD")
        print("="*50 + "\n")
        
        return {
            'prob_local': p_l, 'prob_empate': p_e, 'prob_visita': p_v,
            'ev_local': ev_l, 'apuesta': apuesta_sugerida, 'stake': stake_final
        }

# =====================================================================
# PRUEBA RÁPIDA DEL MOTOR EN ACCIÓN
# =====================================================================
if __name__ == '__main__':
    motor = APEngineV1()
    
    # Ejemplo de prueba con datos simulados de un partido:
    # stats = (goles_prom, tiros_a_puerta_prom, corners_prom, lesiones_clave)
    estadisticas_local = (1.8, 5.5, 6.0, 1)    # Equipo fuerte pero con 1 lesión
    estadisticas_visita = (1.1, 3.2, 4.0, 0)   # Equipo regular sin lesiones
    
    cuotas_casa_de_apuestas = {
        'local': 2.10,   # La casa paga 2.10 si gana el local
        'empate': 3.40,  # 3.40 por el empate
        'visita': 3.60   # 3.60 por la visita
    }
    
    # Analizamos el partido en la consola
    motor.analizar_partido(
        local="Real Madrid",
        visita="Real Sociedad",
        stats_local=estadisticas_local,
        stats_visita=estadisticas_visita,
        cuotas=cuotas_casa_de_apuestas
    )