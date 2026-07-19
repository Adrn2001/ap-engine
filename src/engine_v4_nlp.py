import re
import math

class AnalizadorContextualNLP:
    """
    AP ENGINE 4.0 | Módulo de Procesamiento de Lenguaje Natural (NLP)
    Escanea noticias, reportes de prensa y clima para calcular un Factor Contextual 
    que ajusta dinámicamente el xG de los modelos V2.0 (Dixon-Coles) y V3.0 (XGBoost).
    """
    def __init__(self):
        # Diccionario cuantitativo de impacto competitivo (Pesos de -1.0 a +1.0)
        self.lexico_impacto = {
            # Señales de castigo ofensivo / defensivo (Negativas)
            "suplentes": -0.8, "rotación": -0.6, "lesionado": -0.7, "lesión": -0.7,
            "baja": -0.5, "suspendido": -0.6, "cansancio": -0.4, "crisis": -0.8,
            "duda": -0.3, "molestias": -0.4, "lluvia torrencial": -0.5, "nieve": -0.6,
            "campo pesado": -0.4, "descartado": -0.9, "protesta": -0.7,
            
            # Señales de impulso competitivo (Positivas)
            "titulares": 0.5, "regresa": 0.6, "alta médica": 0.7, "motivado": 0.4,
            "urgencia": 0.5, "estadio lleno": 0.3, "premio doble": 0.6, "racha": 0.4,
            "goleador recuperado": 0.8, "invicto": 0.3, "final anticipada": 0.5
        }
        
        # Límite máximo de impacto sobre el modelo matemático (+-20%)
        self.limite_impacto = 0.20

    def _limpiar_texto(self, texto):
        """Estandariza el texto: minúsculas y eliminación de caracteres de puntuación."""
        if not texto or not isinstance(texto, str):
            return ""
        return re.sub(r'[^\w\s]', '', texto.lower())

    def calcular_sentimiento_lexico(self, texto_noticia):
        """
        Escanea el texto utilizando el diccionario de impacto competitivo.
        Devuelve un Índice de Sentimiento cuantitativo entre -1.0 y +1.0.
        """
        texto_limpio = self._limpiar_texto(texto_noticia)
        if not texto_limpio:
            return 0.0, []

        puntaje_total = 0.0
        coincidencias = []

        # Buscamos términos simples y compuestos en el texto
        for termino, peso in self.lexico_impacto.items():
            if re.search(r'\b' + re.escape(termino) + r'\b', texto_limpio):
                puntaje_total += peso
                coincidencias.append((termino, peso))

        # Aplicamos una función tangente hiperbólica (tanh) para normalizar entre -1 y 1
        # Esto evita que una noticia extremadamente larga distorsione la escala
        sentimiento_normalizado = math.tanh(puntaje_total)
        
        return round(sentimiento_normalizado, 3), coincidencias

    def consultar_llm_externo(self, texto_noticia):
        """
        [HOOK DE PRODUCCIÓN PARA APIS LLM]
        Aquí se puede conectar un cliente de Google Gemini u OpenAI en el futuro
        para análisis semántico profundo si el texto es muy complejo.
        """
        # Ejemplo arquitectónico de retorno:
        # response = gemini_client.generate_content(f"Evalúa impacto deportivo de -1 a 1: {texto_noticia}")
        # return float(response.text)
        pass

    def obtener_factor_contextual(self, texto_local, texto_visita):
        """
        Toma las noticias o reportes de ambos equipos, calcula sus índices de sentimiento
        y devuelve el factor multiplicador exacto para el xG.
        """
        sent_l, cont_l = self.calcular_sentimiento_lexico(texto_local)
        sent_v, cont_v = self.calcular_sentimiento_lexico(texto_visita)

        # Ecuación de modulación contextual: gamma = 1.0 + (Sentimiento * Límite)
        gamma_local = round(1.0 + (sent_l * self.limite_impacto), 3)
        gamma_visita = round(1.0 + (sent_v * self.limite_impacto), 3)

        # Aseguramos acotamiento estricto entre 0.80x y 1.20x
        gamma_local = max(0.80, min(1.20, gamma_local))
        gamma_visita = max(0.80, min(1.20, gamma_visita))

        return {
            'gamma_local': gamma_local,
            'gamma_visita': gamma_visita,
            'sentimiento_local': sent_l,
            'sentimiento_visita': sent_v,
            'señales_local': cont_l,
            'señales_visita': cont_v
        }

    def ajustar_xg_con_nlp(self, xg_base_local, xg_base_visita, factor_ctx):
        """
        Aplica la modulación NLP directamente sobre el xG calculado por 
        Dixon-Coles o los pronósticos pre-partido.
        """
        xg_mod_local = round(xg_base_local * factor_ctx['gamma_local'], 2)
        xg_mod_visita = round(xg_base_visita * factor_ctx['gamma_visita'], 2)
        
        return xg_mod_local, xg_mod_visita

# =====================================================================
# PRUEBA EN VIVO: ESCANEO DE PRENSA Y MODULACIÓN DE xG
# =====================================================================
if __name__ == '__main__':
    nlp_engine = AnalizadorContextualNLP()
    
    print("\n" + "="*65)
    print("📰 AP ENGINE 4.0 | ANÁLISIS DE SENTIMIENTO Y LENGUAJE NATURAL")
    print("="*65)
    
    # Simulación de un escenario de prensa real antes de un partido
    reporte_prensa_local = """
    Última hora en el entrenamiento: El director técnico confirmó que jugarán con suplentes 
    debido a la rotación para la Copa Libertadores. Además, el campo pesado por la lluvia torrencial 
    podría dificultar el juego rápido del equipo. Hay cansancio acumulado.
    """
    
    reporte_prensa_visita = """
    Excelente ambiente en la concentración. El goleador recuperado ha recibido la alta médica 
    y entra en la alineación. El equipo viaja motivado buscando mantener su racha invicto.
    """
    
    # 1. Calculamos los factores contextuales
    analisis = nlp_engine.obtener_factor_contextual(reporte_prensa_local, reporte_prensa_visita)
    
    # 2. Simulamos que el xG cuantitativo base era de 2.10 para el local y 1.40 para la visita
    xg_base_l, xg_base_v = 2.10, 1.40
    xg_mod_l, xg_mod_v = nlp_engine.ajustar_xg_con_nlp(xg_base_l, xg_base_v, analisis)
    
    print("⚽ ESCENARIO PRE-PARTIDO (Sin leer noticias):")
    print(f"   xG Cuantitativo Base ➔ Local: {xg_base_l} | Visita: {xg_base_v}")
    print("-" * 65)
    print("🔬 SEÑALES DETECTADAS POR EL MOTOR NLP:")
    print(f"   🏠 Prensa Local ({analisis['sentimiento_local']} sent.): {[str(k) + f' ({v})' for k, v in analisis['señales_local']]}")
    print(f"   ✈️ Prensa Visita ({analisis['sentimiento_visita']} sent.): {[str(k) + f' ({v})' for k, v in analisis['señales_visita']]}")
    print("-" * 65)
    print("🎯 IMPACTO MATEMÁTICO SOBRE EL PARTIDO:")
    print(f"   Factor Contextual (γ) ➔ Local: {analisis['gamma_local']}x | Visita: {analisis['gamma_visita']}x")
    print(f"   xG Final Modulado   ➔ Local: {xg_base_l} ➔ {xg_mod_l} ({round((analisis['gamma_local']-1)*100, 1)}%)")
    print(f"                       ➔ Visita: {xg_base_v} ➔ {xg_mod_v} ({round((analisis['gamma_visita']-1)*100, 1):+}%)")
    print("="*65 + "\n")