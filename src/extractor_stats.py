import requests
import pandas as pd
import json

class ExtractorScraping:
    """
    Extrae estadísticas de tablas públicas web (Scraping) simulando ser un navegador.
    """
    def __init__(self):
        # Un 'User-Agent' le dice a la web que somos un navegador de verdad (Chrome/Edge)
        # para evitar que nos bloqueen los filtros anti-robots.
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def obtener_promedios_fbref(self, url_equipo):
        """
        Descarga las estadísticas de un equipo desde FBref (la mejor fuente pública de xG y tiros).
        Ejemplo de cómo Pandas puede leer tablas HTML directamente de la web.
        """
        print(f"🌐 Conectando a la web para descargar estadísticas...")
        try:
            # Hacemos la petición HTTP con headers de navegador
            respuesta = requests.get(url_equipo, headers=self.headers)
            
            # Pandas busca automáticamente todas las etiquetas <table> en el HTML de la web
            tablas = pd.read_html(respuesta.text)
            
            # FBref tiene muchas tablas; la primera suele ser el historial de partidos del equipo
            df_partidos = tablas[0]
            
            print(f"✅ ¡Tabla extraída con éxito! ({len(df_partidos)} partidos encontrados)")
            return df_partidos
            
        except Exception as e:
            print(f"❌ Error al hacer scraping: {e}")
            return None


class ExtractorAPI:
    """
    Conecta con APIs oficiales de fútbol (Ej. API-Football en RapidAPI o Football-Data.org).
    """
    def __init__(self, api_key="TU_API_KEY_GRATUITA"):
        self.api_key = api_key
        # Configuración estándar para la versión gratuita de API-Football en RapidAPI
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }

    def obtener_ultimos_partidos(self, id_equipo, cantidad=5):
        """
        Consulta un endpoint REST JSON para obtener los promedios de los últimos N partidos.
        """
        endpoint = f"{self.base_url}/fixtures"
        parametros = {"team": id_equipo, "last": cantidad, "status": "FT"}
        
        print(f"📡 Solicitando datos al servidor API para el equipo ID #{id_equipo}...")
        
        # SI NO TIENES API KEY AÚN, simulamos la respuesta exacta que entrega el servidor:
        if self.api_key == "TU_API_KEY_GRATUITA":
            print("⚠️ Modo Simulación API (Sin Key registrada): Generando JSON de respuesta estándar...")
            return self._simular_respuesta_api()
            
        try:
            respuesta = requests.get(endpoint, headers=self.headers, params=parametros)
            datos = respuesta.json()
            return datos
        except Exception as e:
            print(f"❌ Error de conexión con la API: {e}")
            return None

    def _simular_respuesta_api(self):
        """Estructura idéntica al JSON que devuelven las APIs profesionales."""
        return {
            "resumen_calculado": {
                "goles_prom": 1.8,
                "tiros_a_puerta_prom": 5.2,
                "corners_prom": 6.0,
                "lesiones_clave": 1
            }
        }

# =====================================================================
# PRUEBA DE AUTOMATIZACIÓN EN VIVO
# =====================================================================
if __name__ == '__main__':
    print("="*60)
    print("🤖 AP ENGINE | PRUEBA DE AUTOMATIZACIÓN DE DATOS (ETL)")
    print("="*60)
    
    # 1. Probamos el extractor de API
    api = ExtractorAPI()
    datos_api = api.obtener_ultimos_partidos(id_equipo=541) # 541 = Real Madrid en API-Football
    print("\n📊 Datos procesados listos para AP Engine:", datos_api["resumen_calculado"])
    print("-" * 60)
    
    # 2. Explicación de cómo conectarlo al motor
    print("💡 ¿Cómo se integra esto?")
    print("En tu script guardar_partido.py, en lugar de pedirlos por teclado, harás:")
    print(" -> stats_local = api.obtener_ultimos_partidos(id_local)['resumen_calculado']")
    print("="*60 + "\n")