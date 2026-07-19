import sqlite3
import pandas as pd
import requests
import time
from engine_v1 import APEngineV1
from engine_v3_ml import APEngineV3ML
from modulo_elo import SistemaElo

class BotAlertasTelegram:
    """
    AP ENGINE 5.0 | Módulo de Automatización y Alertas en Vivo (RPA)
    Escanea partidos pendientes en SQLite, calcula probabilidades con los motores V2/V3,
    detecta valor esperado (EV+) y envía alertas push con stakes de Kelly a Telegram.
    """
    def __init__(self, token_bot="", chat_id=""):
        # ⚠️ NOTA: Si en el futuro quieres alertas en tu celular, creas un bot con @BotFather en Telegram
        # y pegas aquí tu token y tu ID. Si se dejan en blanco, el bot imprimirá la alerta en consola.
        self.token = token_bot
        self.chat_id = chat_id
        self.db_path = 'data/ap_engine.db'
        self.umbral_ev_minimo = 3.0  # Solo enviar alerta si el Edge es mayor a +3.0%

    def enviar_mensaje_telegram(self, texto):
        """Envía el mensaje push vía HTTP a los servidores de Telegram o la consola local."""
        if not self.token or not self.chat_id:
            print("\n" + "📲 " + "="*58)
            print(" [SIMULACIÓN DE ALERTA PUSH AL CELULAR - TELEGRAM]")
            print("="*60)
            print(texto)
            print("="*60 + "\n")
            return True

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": texto, "parse_mode": "Markdown"}
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error al conectar con Telegram: {e}")
            return False

    def generar_alerta_pick(self, torneo, local, visita, pick, cuota, ev, stake, motor_usado, prob):
        """Maqueta el mensaje con formato ejecutivo para lectura rápida en el móvil."""
        emoji_motor = "🧬" if "V2.0" in motor_usado else "🤖"
        
        alerta = (
            f"🚨 *¡ALERTA DE VALOR DETECTADA (EV+)!* 🚨\n\n"
            f"🏆 *Torneo:* {torneo}\n"
            f"⚽ *Partido:* {local} vs {visita}\n"
            f"{emoji_motor} *Motor:* {motor_usado}\n"
            f"⚡ *Probabilidad Calculada:* {prob}%\n"
            f"-----------------------------------------\n"
            f"🎯 *APUESTA SUGERIDA:* `{pick}`\n"
            f"📈 *Cuota Bookie:* `{cuota}`\n"
            f"🔥 *Edge (Ventaja Matemática):* `+{ev:.2f}%`\n"
            f"💰 *Stake Sugerido (Half-Kelly):* `${stake} USD`\n"
            f"-----------------------------------------\n"
            f"💡 _La línea de la casa de apuestas presenta ineficiencia por sobre-corrección. Ejecutar orden._"
        )
        return alerta

    def escanear_jornada_y_alertar(self, usar_ia_v3=True):
        """
        Escanea todos los partidos con estatus 'PENDIENTE' en SQLite, corré el algoritmo
        y gatilla las alertas en cuanto detecta ventajas estadísticas.
        """
        print("\n" + "="*65)
        print("🛰️ AP ENGINE 5.0 | DEMONIO DE AUTOMATIZACIÓN Y ALERTAS TELEGRAM")
        print("="*65)
        print("⏳ Conectando a SQLite y escaneando partidos pendientes en el calendario...")
        
        conn = sqlite3.connect(self.db_path)
        query = '''
        SELECT id_partido, fecha, liga, equipo_local, equipo_visitante,
               goles_prom_local, goles_prom_visita, tiros_prom_local, tiros_prom_visita,
               corners_prom_local, corners_prom_visita, lesiones_clave_local, lesiones_clave_visita
        FROM partidos WHERE estatus = 'PENDIENTE'
        '''
        try:
            df_pendientes = pd.read_sql_query(query, conn)
        except Exception:
            df_pendientes = pd.DataFrame()
        conn.close()

        if df_pendientes.empty:
            print("ℹ️ No se encontraron partidos 'PENDIENTES' en la base para auditar.")
            print("💡 Tip: Para ver actuar al bot, simularemos ahora mismo un partido con valor de prueba.")
            self._simular_partido_demo()
            return

        # Inicializamos los motores
        motor_v1 = APEngineV1()
        ai_engine = APEngineV3ML() if usar_ia_v3 else None
        elo_sys = SistemaElo()

        alertas_enviadas = 0

        for idx, row in df_pendientes.iterrows():
            local, visita = row['equipo_local'], row['equipo_visitante']
            stats_l = (row['goles_prom_local'], row['tiros_prom_local'], row['corners_prom_local'], row['lesiones_clave_local'])
            stats_v = (row['goles_prom_visita'], row['tiros_prom_visita'], row['corners_prom_visita'], row['lesiones_clave_visita'])
            
            # Simulamos cuotas ficticias del bookie para el escáner (o las leeríamos de la BD)
            cuota_l, cuota_e, cuota_v = 2.15, 3.40, 3.60
            
            if usar_ia_v3:
                motor_nombre = "V3.0 Machine Learning (XGBoost AI)"
                probs = ai_engine.predecir_partido_ml(stats_l, stats_v)
                p_l, p_e, p_v = probs['prob_local'], probs['prob_empate'], probs['prob_visita']
            else:
                motor_nombre = "V2.0 Cuantitativo (Dixon-Coles + Elo)"
                elo_l, elo_v = elo_sys.obtener_elo(local), elo_sys.obtener_elo(visita)
                f_l, f_v = motor_v1.calcular_factor_elo(elo_l, elo_v)
                xg_l = motor_v1.calcular_xg_ajustado(*stats_l, factor_elo=f_l)
                xg_v = motor_v1.calcular_xg_ajustado(*stats_v, factor_elo=f_v)
                dc = motor_v1.calcular_probabilidades_dixon_coles(xg_l, xg_v)
                p_l, p_e, p_v = dc['1X2']

            # Evaluamos la mejor ineficiencia con Kelly
            ev_l, _, stake_l = motor_v1.evaluar_valor_y_kelly(p_l, cuota_l)
            ev_e, _, stake_e = motor_v1.evaluar_valor_y_kelly(p_e, cuota_e)
            ev_v, _, stake_v = motor_v1.evaluar_valor_y_kelly(p_v, cuota_v)

            if ev_l >= self.umbral_ev_minimo:
                msg = self.generar_alerta_pick(row['liga'], local, visita, f"VICTORIA LOCAL ({local})", cuota_l, ev_l, stake_l, motor_nombre, p_l)
                self.enviar_mensaje_telegram(msg)
                alertas_enviadas += 1
            elif ev_v >= self.umbral_ev_minimo:
                msg = self.generar_alerta_pick(row['liga'], local, visita, f"VICTORIA VISITANTE ({visita})", cuota_v, ev_v, stake_v, motor_nombre, p_v)
                self.enviar_mensaje_telegram(msg)
                alertas_enviadas += 1

        print(f"✅ Escaneo completado. Se enviaron {alertas_enviadas} alertas push en tiempo real.")
        print("="*65 + "\n")

    def _simular_partido_demo(self):
        """Muestra en pantalla el formato exacto de la alerta push en el móvil."""
        print("🧪 GATILLANDO ALERTA DEMO DE PRODUCCIÓN:")
        alerta_demo = self.generar_alerta_pick(
            torneo="Premier League (Inglaterra)",
            local="Arsenal",
            visita="Chelsea",
            pick="VICTORIA LOCAL (Arsenal)",
            cuota=2.25,
            ev=8.40,
            stake=37.50,
            motor_usado="V3.0 Machine Learning (XGBoost AI)",
            prob=48.2
        )
        self.enviar_mensaje_telegram(alerta_demo)

# =====================================================================
# PRUEBA RÁPIDA: EJECUCIÓN DEL DEMONIO DE ALERTAS
# =====================================================================
if __name__ == '__main__':
    bot = BotAlertasTelegram()
    # Ejecutamos el escaneo usando el cerebro de Inteligencia Artificial que entrenamos
    bot.escanear_jornada_y_alertar(usar_ia_v3=True)