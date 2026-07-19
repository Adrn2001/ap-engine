import requests
import json
from datetime import datetime

class ConectorAPIsReal:
    """
    AP ENGINE | Módulo de Conectividad e Ingesta de Datos en Vivo
    Se conecta a servidores internacionales para descargar partidos del día, 
    alineaciones confirmadas y cuotas en tiempo real de casas de apuestas.
    """
    def __init__(self, key_api_sports="", key_the_odds=""):
        # ⚠️ PEGA AQUÍ TUS 2 LLAVES DE ACCESO O PÁSALAS AL INICIALIZAR LA CLASE
        self.key_sports = key_api_sports
        self.key_odds = key_the_odds
        
        # Encabezado de autenticación estándar para API-Football
        self.headers_sports = {
            'x-apisports-key': self.key_sports,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.base_url_sports = "https://v3.football.api-sports.io"
        self.base_url_odds = "https://api.the-odds-api.com/v4/sports"

    def obtener_partidos_del_dia(self, liga_id=242, fecha=None):
        """
        Descarga el calendario real de partidos para una liga en una fecha específica.
        por defecto: liga_id=242 (LigaPro Ecuador), fecha=Hoy.
        """
        if not self.key_sports:
            print("⚠️ Error: Falta la API Key de API-Football.")
            return []
            
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
            
        url = f"{self.base_url_sports}/fixtures"
        params = {"league": liga_id, "season": "2026", "date": fecha}
        
        print(f"⏳ Consultando API-Football para la Liga ID #{liga_id} en fecha {fecha}...")
        try:
            response = requests.get(url, headers=self.headers_sports, params=params, timeout=10)
            data = response.json()
            
            partidos_procesados = []
            for item in data.get("response", []):
                partido = {
                    "id_fixture": item["fixture"]["id"],
                    "fecha": item["fixture"]["date"],
                    "torneo": item["league"]["name"],
                    "local": item["teams"]["home"]["name"],
                    "visita": item["teams"]["away"]["name"],
                    "estatus": item["fixture"]["status"]["short"] # 'NS' = Not Started, 'FT' = Full Time
                }
                partidos_procesados.append(partido)
                
            return partidos_procesados
        except Exception as e:
            print(f"❌ Error en la solicitud HTTP a API-Football: {e}")
            return []

    def obtener_alineaciones_y_bajas(self, fixture_id):
        """
        Consulta si ya salieron las alineaciones oficiales 1 hora antes del partido
        para que nuestro módulo de NLP (v4.0) evalúe si juegan suplentes o titulares.
        """
        if not self.key_sports: return None
        url = f"{self.base_url_sports}/fixtures/lineups"
        params = {"fixture": fixture_id}
        
        try:
            response = requests.get(url, headers=self.headers_sports, params=params, timeout=10)
            data = response.json()
            if not data.get("response"):
                return "Alineaciones aún no disponibles (Suelen publicarse 45 min antes)."
                
            lineups = {}
            for equipo in data["response"]:
                nombre = equipo["team"]["name"]
                formacion = equipo["formation"]
                titulares = [jugador["player"]["name"] for jugador in equipo["startXI"]]
                lineups[nombre] = {"formacion": formacion, "titulares": titulares}
            return lineups
        except Exception as e:
            return f"Error al extraer alineaciones: {e}"

    def obtener_cuotas_en_vivo(self, deporte_key="soccer_fifa_world_cup", regiones="eu,us", mercado="h2h"):
        """
        Se conecta a The-Odds-API y extrae las cuotas en vivo para el mercado 1X2 (h2h)
        desde bookies mundiales como Bet365, Pinnacle o 1xBet.
        """
        if not self.key_odds:
            print("⚠️ Error: Falta la API Key de The-Odds-API.")
            return []
            
        url = f"{self.base_url_odds}/{deporte_key}/odds"
        params = {
            "apiKey": self.key_odds,
            "regions": regiones,
            "markets": mercado, # 'h2h' = 1X2, 'totals' = Over/Under 2.5
            "oddsFormat": "decimal"
        }
        
        print(f"⏳ Consultando The-Odds-API para el mercado: {deporte_key}...")
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if isinstance(data, dict) and data.get("message"):
                print(f"❌ Respuesta del servidor de cuotas: {data['message']}")
                return []
                
            cuotas_procesadas = []
            for evento in data:
                partido_info = {
                    "id_evento": evento["id"],
                    "inicio": evento["commence_time"],
                    "local": evento["home_team"],
                    "visita": evento["away_team"],
                    "casas_apuestas": {}
                }
                
                # Extraemos las cuotas de las primeras 3 casas de apuestas disponibles
                for bookie in evento.get("bookmakers", [])[:3]:
                    nombre_bookie = bookie["title"]
                    mercado_h2h = bookie["markets"][0]["outcomes"]
                    
                    precios = {}
                    for opcion in mercado_h2h:
                        if opcion["name"] == evento["home_team"]:
                            precios["local"] = opcion["price"]
                        elif opcion["name"] == evento["away_team"]:
                            precios["visita"] = opcion["price"]
                        else:
                            precios["empate"] = opcion["price"]
                            
                    partido_info["casas_apuestas"][nombre_bookie] = precios
                cuotas_procesadas.append(partido_info)
                
            return cuotas_procesadas
        except Exception as e:
            print(f"❌ Error al conectar con The-Odds-API: {e}")
            return []

# =====================================================================
# PRUEBA RÁPIDA: VERIFICACIÓN DE CONECTIVIDAD A INTERNET
# =====================================================================
if __name__ == '__main__':
    print("\n" + "="*65)
    print("🛰️ AP ENGINE | TEST DE CONECTIVIDAD A APIS GLOBALES")
    print("="*65)
    
    # ⚠️ PARA PROBAR EN TU CONSOLA, REEMPLAZA LAS CADENAS VACÍAS CON TUS KEYS REALES:
    KEY_SPORTS_DEMO = ""  # Pega aquí tu key de api-sports.io
    KEY_ODDS_DEMO = ""    # Pega aquí tu key de the-odds-api.com
    
    conector = ConectorAPIsReal(key_api_sports=KEY_SPORTS_DEMO, key_the_odds=KEY_ODDS_DEMO)
    
    if not KEY_SPORTS_DEMO and not KEY_ODDS_DEMO:
        print("ℹ️ MODO DEMONSTRACIÓN: No has pegado tus llaves arriba aún.")
        print("💡 Instrucción: Crea tus cuentas gratuitas, pega los códigos en KEY_SPORTS_DEMO")
        print("   y KEY_ODDS_DEMO y vuelve a correr este script para ver llegar datos reales.")
        print("="*65 + "\n")
    else:
        # 1. Probamos traer partidos de la LigaPro de Ecuador (ID 242) o Champions (ID 2)
        partidos = conector.obtener_partidos_del_dia(liga_id=242)
        print(f"\n📊 Partidos descargados desde el servidor: {len(partidos)}")
        for p in partidos[:3]:
            print(f"   ⚽ [{p['estatus']}] {p['torneo']}: {p['local']} vs {p['visita']} ({p['fecha']})")
            
        # 2. Probamos traer cuotas reales en vivo para fútbol internacional
        # En The-Odds-API, las claves de ligas suelen ser: 'soccer_conmebol_libertadores', 'soccer_spain_la_liga', 'soccer_epl', etc.
        cuotas = conector.obtener_cuotas_en_vivo(deporte_key="soccer_spain_la_liga")
        print(f"\n📈 Eventos con cuotas en vivo extraídos: {len(cuotas)}")
        for c in cuotas[:2]:
            print(f"   💵 {c['local']} vs {c['visita']} | Bookies disponibles: {list(c['casas_apuestas'].keys())}")
            if c['casas_apuestas']:
                primera_bookie = list(c['casas_apuestas'].keys())[0]
                print(f"      precios en {primera_bookie}: {c['casas_apuestas'][primera_bookie]}")
        print("="*65 + "\n")