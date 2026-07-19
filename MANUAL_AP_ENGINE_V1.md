# MANUAL TÉCNICO AP ENGINE — VERSIÓN 1.0
**Arquitectura de Software, Metodología Cuantitativa y Gestión de Riesgo Actuarial para Modelado Predictivo en Fútbol**

---

## SECCIÓN 1: FILOSOFÍA DEL MODELO

### 1.1. Ineficiencias de Mercado vs. Adivinación de Marcadores
El objetivo primordial de **AP Engine** es desvincular el análisis deportivo de la intuición humana y el sesgo del aficionado. A diferencia de los apostadores recreativos —que intentan "adivinar" qué equipo ganará un partido—, un motor cuantitativo opera bajo una única premisa actuarial: **la búsqueda de ineficiencias en las cuotas de las casas de apuestas (Value Betting)**.

Una apuesta es rentable a largo plazo si y solo si la probabilidad estimada por el modelo actuarial supera a la probabilidad implícita calculada por el corredor de apuestas ($1 / \text{cuota}$). El sistema no requiere acertar el 100% de los pronósticos; requiere asegurar una **Esperanza Matemática Positiva ($EV+$)** de forma constante en una muestra estadísticamente significativa ($\ge 500$ eventos).

### 1.2. El Paradigma Cuantitativo en Fútbol
El fútbol es un deporte de baja puntuación (*low-scoring game*), lo que incrementa exponencialmente el impacto del azar (varianza) en el resultado final. Un equipo puede dominar el 70% de la posesión, generar 15 remates y perder 0-1 por un evento fortuito. 
Por esta razón, AP Engine no evalúa el mérito en función del marcador final en muestras pequeñas, sino en función de la **generación de volumen ofensivo, la calidad de las oportunidades creadas y la consistencia matemática de las líneas de cierre (CLV)**.

### 1.3. La Relación Híbrida: Motor Matemático (Python) + Motor Contextual (IA)
Para resolver la complejidad del fútbol moderno, AP Engine v1.0 establece una separación estricta de responsabilidades arquitectónicas:
1. **Capa Computacional y Estadístico-Algorítmica (Python / SQLite):** Se encarga de procesar grandes volúmenes de datos numéricos, ejecutar simulaciones estocásticas (Monte Carlo), calcular distribuciones de Poisson y aplicar algoritmos de gestión de capital (Criterio de Kelly). La computadora no alucina números; ejecuta álgebra declarativa.
2. **Capa Cualitativa y Contextual (Modelos de IA / NLP):** Se utiliza para interpretar variables no estructuradas que los modelos matemáticos tradicionales no pueden cuantificar en tiempo real: rotaciones tácticas de última hora, ruedas de prensa ("Mbappé entrenó diferenciado"), motivación condicional (partidos de trámite) y análisis cualitativo del árbitro o clima. La IA actúa como analista que contextualiza los números duros generados por el motor en Python.

---

## SECCIÓN 2: FUENTES DE DATOS Y AUTOMATIZACIÓN (ETL)

### 2.1. Arquitectura de Adquisición de Datos (ETL)
Para eliminar el error humano en la entrada de datos, el proyecto implementa un pipeline de **Extracción, Transformación y Carga (ETL)** modular estructurado en dos capas de recolección:
* **Consumo de APIs REST JSON (Ej. API-Football / Football-Data.org):** Diseñado para la consulta sincrónica y estructurada de calendarios, alineaciones confirmadas, lesionados oficiales, cuotas pre-partido y resultados finales.
* **Web Scraping Asincrónico y Análisis HTML (Pandas / BeautifulSoup4):** Implementado para raspar tablas públicas de estadística avanzada en fuentes libres (ej. FBref, Understat), extrayendo métricas profundas de xG, tiros al arco por partido y métricas disciplinarias que las APIs gratuitas suelen restringir.
### 2.2. Estandarización de Variables (Entradas v1.0)
El modelo v1.0 transforma los datos crudos en variables estandarizadas antes de alimentar el motor estadístico:
* **Promedio de Goles Anotados/Recibidos:** Calculado sobre una ventana móvil ponderada de los últimos 10 partidos oficiales.
* **Ajuste de Volumen de Ataque:** Integración de tiros a puerta y córners generados para corregir anomalías de eficacia goleadora a corto plazo.
* **Factor de Bajas por Lesión:** Ponderación discreta por ausencia de jugadores clasificados como "clave" (más del 60% de minutos jugados en el torneo actual).

### 2.3. Estructura de Persistencia Relacional (SQLite)
Todos los datos son almacenados en una base de datos relacional local (`data/ap_engine.db`), diseñada para soportar consultas analíticas complejas y preparar el terreno para el entrenamiento de modelos de Machine Learning en la v3.0.

#### Esquema de la Tabla `partidos` (Entradas crudas del evento):
| Columna | Tipo de Dato | Descripción |
| :--- | :--- | :--- |
| `id_partido` | `INTEGER PRIMARY KEY` | Identificador autoincremental único del encuentro. |
| `fecha` / `liga` | `TEXT` | Fecha en formato ISO (`YYYY-MM-DD`) y nombre del torneo. |
| `equipo_local` / `equipo_visitante` | `TEXT` | Nombres estandarizados de los clubes contendientes. |
| `goles_prom_local` / `visita` | `REAL` | Promedio de goles anotados en sus últimos 10 encuentros. |
| `tiros_prom_local` / `visita` | `REAL` | Promedio de disparos al arco recientes. |
| `corners_prom_local` / `visita` | `REAL` | Promedio de tiros de esquina generados recientemente. |
| `lesiones_clave_local` / `visita` | `INTEGER` | Conteo de ausencias de jugadores estructurales ($0, 1, 2\dots$). |
| `goles_real_local` / `visita` | `INTEGER NULL` | Marcador final real (se llena al concluir el partido para auditoría). |
| `estatus` | `TEXT` | Estado del registro: `'PENDIENTE'` o `'FINALIZADO'`. |

#### Esquema de la Tabla `historial_predicciones` (Salidas y tracking del motor):
| Columna | Tipo de Dato | Descripción |
| :--- | :--- | :--- |
| `id_prediccion` | `INTEGER PRIMARY KEY` | Identificador autoincremental del pronóstico. |
| `id_partido` | `INTEGER` | Clave foránea relacional apuntando a `partidos(id_partido)`. |
| `version_engine` | `TEXT` | Etiqueta de versión del algoritmo (ej. `'v1.0'`, `'v1.0_ETL'`). |
| `prob_local` / `empate` / `visita` | `REAL` | Probabilidades brutas (%) calculadas para el mercado 1X2. |
| `cuota_bookie_*` | `REAL` | Cuotas decimales de cierre ofrecidas por la casa de apuestas. |
| `ev_local` | `REAL` | Valor Esperado calculado matemáticamente frente al bookie. |
| `apuesta_recomendada` | `TEXT` | Mercado seleccionado con mayor *edge* positivo. |
| `kelly_stake_sugerido` | `REAL` | Monto monetario recomendado a invertir en USD. |
| `resultado_apuesta` | `TEXT NULL` | Estado posterior: `'GANADA'`, `'PERDIDA'` o `'NULA'`. |

---

## SECCIÓN 3: METODOLOGÍA DE CÁLCULO DE PROBABILIDADES

### 3.1. Puntuación Esperada Modificada ($xG$ Simplificado v1.0)
Al no disponer en la v1.0 de feeds telemétricos en tiempo real para calcular coordenadas espaciales de disparo (el $xG$ analítico tradicional), implementamos un algoritmo de **Esperanza de Gol Simplificada ($xG_{adj}$)** que corrige el promedio goleador basándose en la generación de peligro (tiros y córners) y penaliza las bajas estructurales.

La fórmula declarada en el código para cada equipo ($i$) es:

$$xG_{adj, i} = \max\left(0.1, \; \bar{G}_i \times \left[ 1 + 0.03(\bar{T}_i - 4.5) + 0.01(\bar{C}_i - 5.0) \right] \times \max\left(0.5, \; 1 - 0.08 L_i\right)\right)$$

Donde:
* $\bar{G}_i$: Promedio de goles anotados por el equipo $i$ en los últimos partidos.
* $\bar{T}_i$: Promedio de tiros al arco por partido (con línea base de referencia en $4.5$ tiros).
* $\bar{C}_i$: Promedio de tiros de esquina por partido (con línea base de referencia en $5.0$ córners).
* $L_i$: Número entero de lesiones clave ($L_i \in \{0, 1, 2, \dots\}$). Cada lesión clave aplica una penalización discreta del $8\%$ sobre la capacidad goleadora total.

### 3.2. Aplicación de la Distribución de Poisson
La **Distribución de Poisson** es un modelo estadístico ideal para procesos estocásticos de conteo donde los eventos (goles o córners) ocurren de forma independiente y a una tasa promedio constante en un intervalo de tiempo fijo (90 minutos).

La probabilidad de que un equipo anote exactamente $k$ goles en un partido, dada una esperanza de gol calculada de $\lambda = xG_{adj}$, se define mediante la función de masa de probabilidad:

$$P(X = k) = \frac{\lambda^k e^{-\lambda}}{k!}$$

Donde:
* $k$: Número de goles ($0, 1, 2, 3, \dots$).
* $\lambda$: Esperanza de gol o promedio esperado para ese encuentro ($xG_{adj}$).
* $e$: Base de los logaritmos naturales ($\approx 2.71828$).
* $k!$: Factorial del número de goles ($k! = k \times (k-1) \times \dots \times 1$).

### 3.3. Simulación Estocástica por Método de Monte Carlo
En lugar de calcular manualmente la matriz de resultados exactos hasta $k=10$ goles (lo cual es computacionalmente estático), **AP Engine v1.0 implementa el Método de Monte Carlo** usando vectores computacionales en `numpy`.

El algoritmo simula **$N = 10,000$ partidos virtuales independientes** en milisegundos, generando matrices aleatorias de goles para el local ($G_L$) y el visitante ($G_V$) parametrizadas con sus respectivas esperanzas de gol $\lambda_L$ y $\lambda_V$:

$$G_L \sim \text{Poisson}(\lambda_L, \; N=10000), \quad G_V \sim \text{Poisson}(\lambda_V, \; N=10000)$$

A partir de estas matrices vectorizadas de $10,000$ partidos, las probabilidades de cada mercado primario se extraen empíricamente:

$$\text{Probabilidad Victoria Local } (P_L) = \frac{1}{N} \sum_{j=1}^{N} \mathbb{I}(G_{L, j} > G_{V, j}) \times 100$$

$$\text{Probabilidad Empate } (P_E) = \frac{1}{N} \sum_{j=1}^{N} \mathbb{I}(G_{L, j} = G_{V, j}) \times 100$$

$$\text{Probabilidad Victoria Visita } (P_V) = \frac{1}{N} \sum_{j=1}^{N} \mathbb{I}(G_{L, j} < G_{V, j}) \times 100$$

#### Extensión a Mercados Secundarios (Over/Under y Córners):
De manera análoga, el motor escanea los mercados secundarios sumando los vectores de ambas escuadras partido por partido:

$$\text{Probabilidad Over 2.5 Goles} = \frac{1}{N} \sum_{j=1}^{N} \mathbb{I}\left((G_{L, j} + G_{V, j}) > 2.5\right) \times 100$$

Para los tiros de esquina, el sistema aplica una segunda simulación de Poisson independiente utilizando como parámetros $\lambda$ los promedios de córners del local ($\bar{C}_L$) y la visita ($\bar{C}_V$):

$$C_{total} \sim \text{Poisson}(\bar{C}_L, N) + \text{Poisson}(\bar{C}_V, N) \implies P(\text{Over 9.5 Córners}) = \frac{1}{N} \sum_{j=1}^{N} \mathbb{I}(C_{total, j} > 9.5) \times 100$$

---
*Fin de la Parte 1 (Secciones 1 a 3). Las Secciones 4 a 7 profundizan en las matemáticas del Criterio de Kelly, la taxonomía de los reportes y la hoja de ruta hacia Machine Learning.*