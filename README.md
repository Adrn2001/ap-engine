# 🧬 AP ENGINE | Plataforma Cuantitativa & Machine Learning para Análisis Deportivo

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-AI_Tabular-orange?style=for-the-badge&logo=xgboost&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Full_Stack_UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Relational_DB-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-RPA_Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)

**AP Engine** es un ecosistema algorítmico e integral de grado cuantitativo diseñado para la inferencia probabilística, el análisis de valor esperado ($\text{EV}$) y la gestión actuarial del capital en el mercado deportivo de fútbol mundial.

El sistema evoluciona desde distribuciones bivariadas estadísticas clásicas hasta arquitecturas modernas de **Machine Learning (Gradient Boosting)** y **Procesamiento de Lenguaje Natural (NLP)**, operando en vivo a través de un demonio automatizado 24/7 conectado a APIs internacionales y alertas push a dispositivos móviles.

---

## 🏗️ Arquitectura del Sistema

El proyecto está estructurado en un pipeline de datos inmutable que separa la ingesta, el modelado matemático, la inferencia de inteligencia artificial y la capa de presentación:

```mermaid
graph TD
    A[APIs Externas: API-Sports & The-Odds-API] -->|Ingesta REST JSON| B(conector_api.py / ETL)
    B -->|Almacenamiento Inmutable| C[(SQLite: ap_engine.db)]
    
    subgraph Capa Analítica y de Motores
        C -->|Historial Relacional| D[Motor Cuantitativo V2.0]
        C -->|Set de Entrenamiento| E[Motor Machine Learning V3.0]
        D -->|Dixon-Coles 1997 + Elo| F[Cálculo de Probabilidades 1X2]
        E -->|XGBoost Multi-Softprob| F
        G[Reportes de Prensa / Lesiones] -->|Análisis Léxico NLP V4.0| H[Modulador de xG: Factor Gamma]
        H -->|Ajuste Contextual +-20%| F
    end
    
    F --> I[Gestión de Capital: Criterio de Kelly]
    I --> J{Evaluación de Edge: EV >= +3.0%}
    
    J -->|No| K[Descartar Pick / Mercado Eficiente]
    J -->|Sí| L[Demonio RPA V5.0: bot_telegram.py]
    
    L -->|Alerta Push Ejecutiva| M[📲 Telegram / Dispositivo Móvil]
    C -->|Monitoreo en Vivo| N[🖥️ Frontend: Streamlit Web UI]