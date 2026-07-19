import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import os

class APEngineV3ML:
    """
    Cerebro de Inteligencia Artificial - AP ENGINE 3.0
    Entrena y ejecuta modelos predictivos XGBoost sobre la base de datos histórica relacional.
    """
    def __init__(self, db_path='data/ap_engine.db', model_path='models/ap_engine_v3_xgboost.json'):
        self.db_path = db_path
        self.model_path = model_path
        self.features = [
            'goles_prom_local', 'goles_prom_visita', 
            'tiros_prom_local', 'tiros_prom_visita',
            'corners_prom_local', 'corners_prom_visita', 
            'lesiones_clave_local', 'lesiones_clave_visita'
        ]
        os.makedirs('models', exist_ok=True)
        self.modelo = None

    def cargar_datos_entrenamiento(self):
        """Extrae el historial de partidos finalizados desde SQLite para alimentar a la IA."""
        conn = sqlite3.connect(self.db_path)
        query = '''
        SELECT goles_prom_local, goles_prom_visita, tiros_prom_local, tiros_prom_visita,
               corners_prom_local, corners_prom_visita, lesiones_clave_local, lesiones_clave_visita,
               CASE 
                   WHEN goles_real_local > goles_real_visita THEN 0  -- 0 = Gana Local
                   WHEN goles_real_local = goles_real_visita THEN 1  -- 1 = Empate
                   ELSE 2                                            -- 2 = Gana Visita
               END as target_resultado
        FROM partidos 
        WHERE estatus = 'FINALIZADO' AND goles_real_local IS NOT NULL
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def entrenar_y_evaluar(self):
        """Entrena el clasificador XGBoost y evalúa su precisión matemática."""
        print("\n" + "="*65)
        print("🧠 AP ENGINE 3.0 | ENTRENAMIENTO DE MACHINE LEARNING (XGBOOST)")
        print("="*65)
        
        df = self.cargar_datos_entrenamiento()
        print(f"📊 Leyendo {len(df)} partidos históricos desde SQLite para entrenamiento...")
        
        if len(df) < 50:
            print("❌ Error: Necesitas al menos 50 partidos en la base para entrenar un modelo robusto.")
            return False

        # 1. Separar características (X) y el resultado real en cancha (y)
        X = df[self.features]
        y = df['target_resultado']

        # 2. Dividir: 80% de los partidos para estudiar (train) y 20% para examen final (test)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
        
        print(f"🔬 Set de Entrenamiento: {len(X_train)} partidos | Set de Examen: {len(X_test)} partidos")
        
        # 3. Configurar y entrenar el árbol de decisión XGBoost
        self.modelo = xgb.XGBClassifier(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='multi:softprob', # Entrega probabilidad exacta para Local, Empate y Visita
            random_state=42
        )
        
        print("⏳ Entrenando árboles de decisión y descubriendo patrones ocultos...")
        self.modelo.fit(X_train, y_train)
        
        # 4. Examen de Precisión (Probamos el modelo contra el 20% que nunca vio)
        predicciones_clase = self.modelo.predict(X_test)
        precision = accuracy_score(y_test, predicciones_clase) * 100
        
        print("-" * 65)
        print(f"🏆 PRECISIÓN GENERAL DE LA IA: {precision:.2f}% en datos no vistos")
        print("-" * 65)
        
        # Desglose de precisión por mercado
        nombres_clases = ['Gana Local', 'Empate', 'Gana Visita']
        print("📋 Reporte Estructural por Tipo de Mercado:")
        print(classification_report(y_test, predicciones_clase, target_names=nombres_clases, zero_division=0))
        
        # 5. Guardar el modelo en disco
        self.modelo.save_model(self.model_path)
        print(f"💾 Modelo de IA guardado en '{self.model_path}' listo para producción y web.")
        print("="*65 + "\n")
        return True

    def predecir_partido_ml(self, stats_local, stats_visita):
        """
        Toma estadísticas en tiempo real y usa el archivo de IA para predecir.
        stats_local/visita = (goles, tiros, corners, lesiones)
        """
        if not self.modelo:
            self.modelo = xgb.XGBClassifier()
            if os.path.exists(self.model_path):
                self.modelo.load_model(self.model_path)
            else:
                print("⚠️ No hay modelo entrenado guardado aún. Ejecuta entrenar_y_evaluar() primero.")
                return None
                
        # Armamos el vector de datos idéntico a cómo aprendió en el entrenamiento
        vector_entrada = pd.DataFrame([[
            stats_local[0], stats_visita[0],
            stats_local[1], stats_visita[1],
            stats_local[2], stats_visita[2],
            stats_local[3], stats_visita[3]
        ]], columns=self.features)
        
        # La IA calcula la probabilidad de los 3 resultados al instante
        probabilidades = self.modelo.predict_proba(vector_entrada)[0]
        
        # Convertimos de numpy.float32 a float nativo de Python
        return {
            'prob_local': round(float(probabilidades[0]) * 100, 2),
            'prob_empate': round(float(probabilidades[1]) * 100, 2),
            'prob_visita': round(float(probabilidades[2]) * 100, 2)
        }

# =====================================================================
# PRUEBA RÁPIDA: ENTRENAR E INFERIR CON IA
# =====================================================================
if __name__ == '__main__':
    ai_engine = APEngineV3ML()
    
    # 1. Entrenar el modelo con los 760 partidos que acabas de importar
    exito = ai_engine.entrenar_y_evaluar()
    
    if exito:
        # 2. Hacemos una prueba de predicción en milisegundos
        print("🧪 PRUEBA EN VIVO CON IA ENTRENADA:")
        stats_l = (2.1, 6.8, 6.2, 0) # Equipo local fuerte y sin lesionados
        stats_v = (1.1, 3.5, 4.0, 1) # Equipo visitante débil con 1 lesión
        
        probs = ai_engine.predecir_partido_ml(stats_l, stats_v)
        print(f"🎯 Probabilidades predichas por XGBoost ➔ Local: {probs['prob_local']}% | Empate: {probs['prob_empate']}% | Visita: {probs['prob_visita']}%")
        print("="*65 + "\n")