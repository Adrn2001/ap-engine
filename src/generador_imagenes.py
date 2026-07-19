from PIL import Image, ImageDraw, ImageFont
import os

class GeneradorTarjetasVIP:
    """
    AP ENGINE 7.0 | Renderizador Gráfico de Tarjetas VIP
    Toma los datos procesados por el Motor Francotirador y genera una imagen PNG
    estilo 'Dashboard Dark Mode' para enviar vía sendPhoto en Telegram.
    """
    def __init__(self):
        # Colores de la paleta profesional Dark Mode (RGB)
        self.color_fondo = (24, 27, 34)         # Gris muy oscuro (#181B22)
        self.color_caja = (36, 40, 50)          # Gris contenedor (#242832)
        self.color_texto = (240, 240, 240)      # Blanco suave
        self.color_gris = (160, 165, 175)       # Gris secundario para subtítulos
        self.color_verde = (46, 204, 113)       # Verde (Conservadora)
        self.color_amarillo = (241, 196, 15)    # Amarillo (Equilibrada)
        self.color_naranja = (230, 126, 34)     # Naranja (Jugada)
        
        # Intentamos cargar fuentes limpias de Windows (Segoe UI o Arial)
        try:
            self.f_titulo = ImageFont.truetype("segoeuib.ttf", 28)
            self.f_subtitulo = ImageFont.truetype("segoeui.ttf", 18)
            self.f_tier = ImageFont.truetype("segoeuib.ttf", 20)
            self.f_cuota = ImageFont.truetype("segoeuib.ttf", 24)
            self.f_texto = ImageFont.truetype("segoeui.ttf", 16)
        except IOError:
            # Si no encuentra Segoe UI, usa la fuente por defecto del sistema
            self.f_titulo = ImageFont.load_default()
            self.f_subtitulo = ImageFont.load_default()
            self.f_tier = ImageFont.load_default()
            self.f_cuota = ImageFont.load_default()
            self.f_texto = ImageFont.load_default()

    def _dibujar_caja_combinada(self, draw, x, y, ancho, alto, combi, color_borde):
        """Dibuja cada una de las 3 opciones con bordes redondeados y estructura limpia."""
        # Contenedor de fondo
        draw.rounded_rectangle([x, y, x + ancho, y + alto], radius=12, fill=self.color_caja, outline=color_borde, width=2)
        
        # Título del Tier (Ej. COMBINADA CONSERVADORA)
        draw.text((x + 20, y + 15), combi['tier'][:28], fill=color_borde, font=self.f_tier)
        
        # Cuota y Probabilidad en el extremo derecho
        txt_cuota = f"Cuota: {combi['cuota_betano']}"
        txt_prob = f"{combi['probabilidad']}% Prob"
        draw.text((x + ancho - 180, y + 15), txt_cuota, fill=self.color_texto, font=self.f_cuota)
        draw.text((x + ancho - 180, y + 45), txt_prob, fill=color_borde, font=self.f_subtitulo)
        
        # Línea divisoria interna
        draw.line([x + 20, y + 75, x + ancho - 20, y + 75], fill=(60, 65, 80), width=1)
        
        # Listado de los picks de Betano
        pos_y = y + 90
        draw.text((x + 20, pos_y), "Selecciones en Bet Builder:", fill=self.color_gris, font=self.f_subtitulo)
        pos_y += 25
        
        for idx, pick in enumerate(combi['picks'], 1):
            draw.text((x + 30, pos_y), f"▪  {pick}", fill=self.color_texto, font=self.f_texto)
            pos_y += 25
            
        # Justificación o nota inferior
        pos_y = y + alto - 35
        nota_corta = combi['justificacion'][:65] + "..." if len(combi['justificacion']) > 65 else combi['justificacion']
        draw.text((x + 20, pos_y), f"NOTA: {nota_corta}", fill=self.color_gris, font=self.f_texto)

    def generar_imagen_vip(self, combinadas, contexto, ruta_salida="data/tarjeta_vip.png"):
        """
        Ensambla el dashboard gráfico en una imagen PNG y devuelve la ruta del archivo.
        """
        # Aseguramos que la carpeta data exista
        os.makedirs("data", exist_ok=True)
        
        ancho, alto = 800, 960
        img = Image.new("RGB", (ancho, alto), color=self.color_fondo)
        draw = ImageDraw.Draw(img)
        
        # 1. CABECERA VIP
        draw.rectangle([0, 0, ancho, 100], fill=(30, 35, 45))
        draw.text((30, 20), "AP ENGINE VIP | BETANO BET BUILDER", fill=self.color_texto, font=self.f_titulo)
        
        sub_txt = f"PARTIDO: {contexto['partido']}   |   ARBITRO: {contexto['arbitro']['nombre']}"
        draw.text((30, 60), sub_txt, fill=self.color_gris, font=self.f_subtitulo)
        
        # Indicador visual de rigurosidad de tarjetas
        estado_tarjetas = "⚡ TARJETAS ABIERTAS" if contexto['arbitro']['es_riguroso'] else "🛑 TARJETAS BLOQUEADAS"
        color_tarj = self.color_verde if contexto['arbitro']['es_riguroso'] else self.color_naranja
        draw.rounded_rectangle([ancho - 240, 30, ancho - 30, 70], radius=8, fill=color_tarj)
        draw.text((ancho - 230, 40), estado_tarjetas, fill=(0, 0, 0), font=self.f_subtitulo)
        
        # 2. DIBUJAR LAS 3 CAJAS DE COMBINADAS (Conservadora, Equilibrada, Jugada)
        colores_tier = [self.color_verde, self.color_amarillo, self.color_naranja]
        pos_y_caja = 130
        alto_caja = 240
        
        for idx, combi in enumerate(combinadas):
            color = colores_tier[idx] if idx < len(colores_tier) else self.color_texto
            self._dibujar_caja_combinada(draw, 30, pos_y_caja, ancho - 60, alto_caja, combi, color)
            pos_y_caja += alto_caja + 20
            
        # 3. PIE DE PÁGINA
        draw.text((30, alto - 40), "🤖 Generado automáticamente por AP Engine 7.0 | Gestión de Capital Kelly", fill=(100, 105, 115), font=self.f_texto)
        
        # Guardar archivo en el disco duro
        img.save(ruta_salida, "PNG")
        print(f"🖼️ ¡Imagen VIP generada exitosamente en: {ruta_salida}!")
        return ruta_salida

# =====================================================================
# PRUEBA EN VIVO: GENERAR UNA TARJETA DE EJEMPLO EN TU PC
# =====================================================================
if __name__ == '__main__':
    from motor_francotirador import MotorFrancotiradorBetano
    
    motor = MotorFrancotiradorBetano()
    combis, ctx = motor.generar_3_combinadas_betano("Barcelona SC", "Emelec")
    
    gen = GeneradorTarjetasVIP()
    ruta_foto = gen.generar_imagen_vip(combis, ctx)
    print("💡 Ve a tu carpeta 'data/' y abre 'tarjeta_vip.png' para ver tu diseño gráfico.")