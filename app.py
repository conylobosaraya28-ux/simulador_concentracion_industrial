import streamlit as st
import math
import random
import pandas as pd
import plotly.express as px
from typing import List, Union

# ==========================================
# 1. FUNCIONES BASE
# ==========================================

def _validar_y_normalizar_cuotas(cuotas: List[Union[int, float]]) -> List[float]:
    if not cuotas:
        raise ValueError("La lista de cuotas no puede estar vacía.")
    if any(c <= 0 for c in cuotas):
        raise ValueError("Todas las cuotas de mercado deben ser estrictamente mayores a 0.")
    suma_total = sum(cuotas)
    return [c / suma_total for c in cuotas]

def calcular_cr_k(cuotas: List[Union[int, float]], k: int) -> float:
    cuotas_norm = _validar_y_normalizar_cuotas(cuotas)
    cuotas_ordenadas = sorted(cuotas_norm, reverse=True)
    return sum(cuotas_ordenadas[:k])

def calcular_ihh(cuotas: List[Union[int, float]]) -> float:
    cuotas_norm = _validar_y_normalizar_cuotas(cuotas)
    return sum(c**2 for c in cuotas_norm)

def calcular_id(cuotas: List[Union[int, float]]) -> float:
    cuotas_norm = _validar_y_normalizar_cuotas(cuotas)
    ihh = calcular_ihh(cuotas_norm)
    return sum(((c**2) / ihh)**2 for c in cuotas_norm)

def calcular_ie(cuotas: List[Union[int, float]]) -> float:
    cuotas_norm = _validar_y_normalizar_cuotas(cuotas)
    return sum(c * math.log(1 / c) for c in cuotas_norm)

def simular_cuotas_monte_carlo(n_empresas: int, iteraciones: int = 1000) -> List[List[float]]:
    simulaciones = []
    for _ in range(iteraciones):
        valores = [random.expovariate(1.0) for _ in range(n_empresas)]
        suma_valores = sum(valores)
        cuotas = [v / suma_valores for v in valores]
        simulaciones.append(cuotas)
    return simulaciones

def evaluar_nivel_teorico(indicador: str, valor: float, n_empresas: int):
    """Retorna la clasificación teórica y la justificación económica."""
    if "IHH" in indicador:
        if valor < 0.15: return "Baja Concentración", "El DOJ y la FTC consideran mercados no concentrados cuando el IHH es inferior a 1500 (0.15 en esta escala). Indica alta competencia."
        elif valor <= 0.25: return "Concentración Moderada", "Se considera un mercado moderadamente concentrado cuando el IHH está entre 1500 (0.15) y 2500 (0.25)."
        else: return "Alta Concentración", "Un IHH superior a 2500 (0.25) indica un mercado altamente concentrado con posible poder de mercado oligopólico o monopólico."
    
    elif "CR_k" in indicador:
        if valor < 0.40: return "Baja Concentración", "Un ratio inferior al 40% sugiere que el mercado opera bajo competencia monopolística o perfecta, sin un claro dominio de las firmas líderes."
        elif valor <= 0.70: return "Concentración Moderada", "Un CR_k entre 40% y 70% indica una estructura oligopólica moderada."
        else: return "Alta Concentración", "Un CR_k superior a 70% señala un oligopolio fuerte o un mercado cercano al monopolio."
        
    elif "IE" in indicador:
        # Entropía máxima es ln(N). Se normaliza para evaluar.
        e_max = math.log(n_empresas)
        ratio = valor / e_max if e_max > 0 else 0
        if ratio > 0.8: return "Baja Concentración", f"La entropía es alta (cercana al máximo ln({n_empresas})={e_max:.2f}), implicando cuotas dispersas y simétricas."
        elif ratio >= 0.6: return "Concentración Moderada", "La entropía muestra cierta asimetría y varianza en las cuotas de mercado."
        else: return "Alta Concentración", "Una entropía baja denota que unas pocas empresas acumulan casi todo el mercado, reflejando alta concentración."
        
    elif "ID" in indicador:
        if valor < 0.15: return "Baja Concentración", "Un ID bajo muestra que ninguna empresa sesga desproporcionadamente la estructura del mercado."
        elif valor <= 0.25: return "Concentración Moderada", "El ID indica participaciones relevantes que comienzan a sesgar el índice agregado."
        else: return "Alta Concentración", "Un ID superior a 0.25 señala asimetrías severas con empresas fuertemente dominantes."

# ==========================================
# 2. APLICACIÓN STREAMLIT
# ==========================================

st.set_page_config(page_title="Simulador de Concentración Industrial", layout="wide")
st.title("Simulador y Evaluador de Concentración Industrial")
st.markdown("Esta aplicación permite simular distribuciones estocásticas de índices económicos, analizar casos particulares y evaluar tu conocimiento sobre la estructura del mercado.")

# --- INICIALIZAR VARIABLES DE ESTADO ---
# Necesario para que la app no pierda la simulación al usar el radio button
if "sim_data" not in st.session_state:
    st.session_state.sim_data = None

# --- BARRA LATERAL (Sidebar) ---
st.sidebar.header("Configuración")

# ADVERTENCIA DE CARGA COMPUTACIONAL
st.sidebar.warning(
    "**Advertencia de Carga Computacional:**\n"
    "Incrementar significativamente el número de iteraciones (ej. > 10,000) o de empresas incrementará "
    "el uso de CPU/RAM. Esto puede causar mayor latencia y un incremento en el tiempo de respuesta."
)

indicador_seleccionado = st.sidebar.selectbox(
    "Selecciona el Indicador", 
    ["Índice de Herfindahl-Hirschman (IHH)", 
     "Ratio de Concentración (CR_k)", 
     "Índice de Dominancia (ID)", 
     "Índice de Entropía (IE)"]
)

n_empresas = st.sidebar.slider("Número de Empresas (N)", min_value=2, max_value=100, value=10)
iteraciones = st.sidebar.number_input("Número de Iteraciones (Monte Carlo)", min_value=100, max_value=100000, value=1000, step=1000)

k_val = None
if indicador_seleccionado == "Ratio de Concentración (CR_k)":
    k_val = st.sidebar.slider("Valor de 'k' (Empresas más grandes)", min_value=1, max_value=n_empresas-1, value=min(4, n_empresas-1))

ejecutar = st.sidebar.button("Generar y Simular", type="primary")

# --- LÓGICA DE SIMULACIÓN ---
if ejecutar:
    with st.spinner("Ejecutando simulación de Monte Carlo..."):
        caso_particular = simular_cuotas_monte_carlo(n_empresas, 1)[0]
        
        if "IHH" in indicador_seleccionado:
            val_particular = calcular_ihh(caso_particular)
        elif "CR_k" in indicador_seleccionado:
            val_particular = calcular_cr_k(caso_particular, k_val)
        elif "ID" in indicador_seleccionado:
            val_particular = calcular_id(caso_particular)
        elif "IE" in indicador_seleccionado:
            val_particular = calcular_ie(caso_particular)
            
        simulaciones = simular_cuotas_monte_carlo(n_empresas, iteraciones)
        
        resultados_mc = []
        for sim in simulaciones:
            if "IHH" in indicador_seleccionado:
                resultados_mc.append(calcular_ihh(sim))
            elif "CR_k" in indicador_seleccionado:
                resultados_mc.append(calcular_cr_k(sim, k_val))
            elif "ID" in indicador_seleccionado:
                resultados_mc.append(calcular_id(sim))
            elif "IE" in indicador_seleccionado:
                resultados_mc.append(calcular_ie(sim))
                
        # Guardar todo en Session State para persistencia al evaluar
        st.session_state.sim_data = {
            "indicador": indicador_seleccionado,
            "n_empresas": n_empresas,
            "val_particular": val_particular,
            "df_resultados": pd.DataFrame({indicador_seleccionado: resultados_mc}),
            "caso_particular": caso_particular
        }

# --- VISUALIZACIÓN Y MÓDULO EVALUADOR ---
if st.session_state.sim_data is not None:
    data = st.session_state.sim_data
    
    st.divider()
    st.subheader(f"Resultados para {data['indicador']}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info(f"**Valor del Caso Particular:**\n### {data['val_particular']:.4f}")
        cuotas_ordenadas = sorted(data['caso_particular'], reverse=True)
        df_cuotas = pd.DataFrame({
            "Empresa (Rank)": [f"Empresa {i+1}" for i in range(len(cuotas_ordenadas))],
            "Cuota (%)": [c * 100 for c in cuotas_ordenadas]
        })
        st.dataframe(df_cuotas.style.format({"Cuota (%)": "{:.2f}%"}), height=300)

    with col2:
        fig = px.histogram(
            data['df_resultados'], 
            x=data['indicador'], 
            nbins=50, 
            title="Distribución Monte Carlo",
            color_discrete_sequence=['#4C78A8'],
            marginal="box"
        )
        fig.add_vline(
            x=data['val_particular'], line_dash="dash", line_color="red", line_width=3,
            annotation_text=f"Caso Actual", annotation_position="top right"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # MÓDULO EVALUADOR INTERACTIVO
    # ==========================================
    st.divider()
    st.subheader("Módulo Evaluador: Pon a prueba tu análisis")
    st.write(f"Observando el valor del indicador calculado (**{data['val_particular']:.4f}**), clasifica este mercado:")
    
    respuesta_usuario = st.radio(
        "¿Cuál es el nivel de concentración de esta industria?",
        ["Baja Concentración", "Concentración Moderada", "Alta Concentración"],
        index=None,
        horizontal=True
    )
    
    if respuesta_usuario:
        # 1. Cálculo de Posición Cuantitativa (Percentil exacto)
        serie_resultados = data['df_resultados'][data['indicador']]
        if "IE" in data['indicador']:
            # Para Entropía, valores altos = menor concentración
            percentil = (serie_resultados < data['val_particular']).mean() * 100
            txt_percentil = f"Este valor de entropía supera al **{percentil:.2f}%** de los escenarios simulados."
        else:
            percentil = (serie_resultados < data['val_particular']).mean() * 100
            txt_percentil = f"Este nivel de concentración es mayor que el **{percentil:.2f}%** de los escenarios simulados."
            
        # 2. Obtener retroalimentación teórica
        nivel_correcto, explicacion = evaluar_nivel_teorico(data['indicador'], data['val_particular'], data['n_empresas'])
        
        # 3. Despliegue de Validación y Retroalimentación
        if respuesta_usuario == nivel_correcto:
            st.success(f"¡Correcto! Has clasificado bien el mercado como: **{nivel_correcto}**.")
        else:
            st.error(f"Incorrecto. La clasificación teórica apropiada es: **{nivel_correcto}**.")
            
        with st.expander("Ver Explicación Técnica y Posición Cuantitativa", expanded=True):
            st.markdown(f"**Justificación Teórica:**\n{explicacion}")
            st.markdown(f"**Posición Cuantitativa (Monte Carlo):**\n{txt_percentil} Dentro de un mercado de {data['n_empresas']} empresas estructurado aleatoriamente, estar en el percentil {percentil:.1f} revela qué tan típico o extremo es este grado de asimetría.")