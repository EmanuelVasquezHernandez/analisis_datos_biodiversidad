# app.py
# Interfaz principal de la aplicación BioData Manager hecha con Streamlit.

import streamlit as st  # Importo Streamlit para crear la app web
import pandas as pd     # Importo pandas para manejar las tablas de datos
from pathlib import Path  # Importo Path para manejar rutas de archivos

from utils import (
    leer_archivo_subido,     # Función que uso para leer los archivos cargados (csv/xlsx)
    limpiar_dataframe,       # Función que limpia y estandariza la columna de especie
    construir_interseccion,  # Función que calcula las especies coincidentes entre las fuentes
)

# ----------------------------------------------------------------------
# CONFIGURACIÓN INICIAL DE LA PÁGINA
# ----------------------------------------------------------------------

logo_path = Path("assets/logo.png")  # Defino la ruta donde guardé el logo de la app
page_icon = str(logo_path) if logo_path.exists() else "🪴"  # Uso el logo si existe, si no un emoji

st.set_page_config(             # Configuro la página principal de Streamlit
    page_title="BioData Manager",  # Título que se ve en la pestaña del navegador
    page_icon=page_icon,          # Ícono de la pestaña (logo o emoji)
    layout="wide",                # Uso el layout ancho para aprovechar la pantalla completa
)

css_path = Path("assets/styles.css")  # Ruta del archivo CSS con los estilos personalizados
if css_path.exists():                 # Si el css existe lo cargo
    with open(css_path) as f:         # Abro el archivo
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)  # Inyecto el CSS en la página

# ----------------------------------------------------------------------
# ESTADO: NÚMERO DE FUENTES
# ----------------------------------------------------------------------

if "num_sources" not in st.session_state:  # Si es la primera vez que corro la app
    st.session_state.num_sources = 3       # Empiezo con 3 fuentes (por ejemplo SIB, GBIF, IUCN)

num_sources = st.session_state.num_sources  # Guardo el número de fuentes en una variable local
default_names = ["SIB", "GBIF", "IUCN"]     # Nombres por defecto de las tres primeras fuentes
columna_estandar = "scientificName"         # Nombre estándar que voy a usar para la columna de especie

# ----------------------------------------------------------------------
# SHELL DE LA APP (LOGO + HEADER + CONTENEDOR PRINCIPAL)
# ----------------------------------------------------------------------

st.markdown('<div class="app-shell">', unsafe_allow_html=True)  # Inicio el contenedor general de la app

# Logo centrado usando columnas
if logo_path.exists():                                # Si el logo existe
    col_left, col_center, col_right = st.columns([1, 2, 1])  # Creo tres columnas para centrarlo
    with col_center:                                  # Pongo el logo en la columna central
        st.image(str(logo_path), width=580)           # Muestro el logo con un ancho grande

st.markdown('<div class="biodata-header">BioData Manager</div>', unsafe_allow_html=True)  # Barra con el título de la app
st.markdown('<div class="main-card">', unsafe_allow_html=True)   # Contenedor principal tipo “tarjeta”

# ----------------------------------------------------------------------
# ENCABEZADO Y BUSCADOR
# ----------------------------------------------------------------------

st.markdown(                                          
    '<div class="app-section-title">Panel de análisis de especies</div>',  # Título de la sección principal
    unsafe_allow_html=True,
)

st.markdown(                                          # Texto explicando qué hace este panel
    '<div class="app-section-text">'
    "Carga tus bases de datos de biodiversidad, indica la columna del nombre científico en cada una "
    "y luego busca especies coincidentes entre las fuentes."
    "</div>",
    unsafe_allow_html=True,
)

busqueda = st.text_input(                             # Cuadro de texto para filtrar especies por nombre
    "Buscar especies",                                # Etiqueta interna
    value="",                                         # Empieza vacío
    placeholder="Buscar especies",                    # Texto guía dentro del input
)

st.markdown("")                                       # Pequeño espacio visual

# ----------------------------------------------------------------------
# SECCIÓN: FUENTES DE DATOS (DINÁMICA)
# ----------------------------------------------------------------------

st.markdown('<div class="app-section-title">Fuentes de datos</div>', unsafe_allow_html=True)  # Título de la sección de fuentes
st.markdown(
    '<div class="app-section-text">'
    "Sube tantas bases de datos como necesites (SIB, GBIF, IUCN u otras). "
    "En cada tarjeta define la columna donde está el nombre científico y, si quieres, "
    "una columna extra cuya información se agregará a la tabla final."
    "</div>",
    unsafe_allow_html=True,
)

# Tarjetas de fuentes en filas de 3
for start in range(0, num_sources, 3):         # Recorro las fuentes de 3 en 3 para hacer filas
    cols = st.columns(3)                       # Creo 3 columnas para cada fila
    for i in range(start, min(start + 3, num_sources)):  # Recorro los índices dentro de la fila
        fuente_idx = i                         # Índice de la fuente actual
        nombre_base = default_names[i] if i < len(default_names) else f"Fuente {i+1}"  # Nombre visible de la fuente

        with cols[i - start]:                  # Pinto el contenido en la columna que le corresponde
            st.caption(nombre_base)            # Muestro el nombre de la fuente como caption

            st.file_uploader(                  # Widget para subir el archivo de la fuente
                f"Archivo {nombre_base} (CSV / Excel)",  # Texto interno
                type=["csv", "xlsx"],                  # Tipos permitidos
                key=f"file_{fuente_idx}",              # Clave única en session_state
                label_visibility="collapsed",          # Oculto la etiqueta para que se vea más limpio
            )

            st.text_input(                      # Input para que el usuario escriba la columna de especie
                f"Columna de especie en {nombre_base}",
                value="scientificName",         # Valor por defecto
                key=f"species_col_{fuente_idx}",  # Clave en session_state
            )

            st.text_input(                      # Input para que el usuario pueda añadir una columna extra opcional
                f"Columna extra a añadir desde {nombre_base} (opcional)",
                value="",                       # Empieza vacío
                key=f"extra_col_{fuente_idx}",  # Clave en session_state
            )

# Botón para agregar más fuentes
if st.button("➕ Agregar otra fuente"):      # Si doy clic en el botón de agregar fuente
    st.session_state.num_sources += 1       # Aumento en 1 el número de fuentes
    st.rerun()                              # Recargo la app para que aparezca la nueva tarjeta de entrada

# ----------------------------------------------------------------------
# CARGA A DATAFRAMES Y VISTA RÁPIDA
# ----------------------------------------------------------------------

sources_info = []                           # Aquí voy a guardar la info de cada fuente (diccionarios)

for i in range(num_sources):                # Recorro todas las posibles fuentes
    file_obj = st.session_state.get(f"file_{i}")  # Recupero el archivo subido para la fuente i
    if file_obj is not None:               # Si hay archivo cargado
        nombre_base = default_names[i] if i < len(default_names) else f"Fuente {i+1}"  # Nombre de la fuente
        species_col = st.session_state.get(f"species_col_{i}", "")  # Nombre de la columna de especie
        extra_col = st.session_state.get(f"extra_col_{i}", "")      # Nombre de la columna extra

        df_raw = leer_archivo_subido(file_obj)  # Leo el archivo (csv/xlsx) y lo convierto en DataFrame

        sources_info.append(              # Agrego la info de esta fuente a la lista
            {
                "name": nombre_base,      # Nombre
                "df_raw": df_raw,         # DataFrame original
                "species_col": species_col,      # Columna de especie
                "extra_col": extra_col.strip(),  # Columna extra (le quito espacios a los lados)
            }
        )

st.markdown("---")                         # Separador visual
st.markdown(
    '<div class="app-section-title">Vista rápida de las bases cargadas</div>',  # Título de la vista previa
    unsafe_allow_html=True,
)

if sources_info:                            # Si tengo al menos una fuente con datos
    for start in range(0, len(sources_info), 3):  # Las muestro de 3 en 3
        cols = st.columns(3)               # 3 columnas por fila
        for j in range(start, min(start + 3, len(sources_info))):  # Recorro esa fila
            src = sources_info[j]          # Tomo la fuente actual
            with cols[j - start]:          # Me ubico en su columna
                st.caption(src["name"])    # Muestro el nombre de la fuente
                st.write(src["df_raw"].head())  # Muestro las primeras filas del DataFrame
else:
    st.write("Aún no se ha cargado ninguna base de datos.")  # Mensaje si no hay datos

st.markdown("---")                         # Otro separador visual

# ----------------------------------------------------------------------
# BOTÓN PARA PROCESAR COINCIDENCIAS
# ----------------------------------------------------------------------

procesar = st.button("🔍 Procesar y buscar especies coincidentes")  # Botón para lanzar todo el procesamiento

if procesar:                               # Si el usuario hizo clic en procesar

    if not sources_info:                   # Si no hay ninguna fuente cargada
        st.error("Por favor, carga al menos una base de datos en las tarjetas de arriba.")
    else:
        try:
            fuentes_limpias: dict[str, pd.DataFrame] = {}  # Aquí guardo los DataFrames limpios
            extra_cols_map: dict[str, str] = {}            # Aquí guardo qué columna extra usar de cada fuente

            # 1. Limpieza por fuente
            for src in sources_info:                       # Recorro cada fuente cargada
                nombre = src["name"]                       # Nombre de la fuente
                df_raw = src["df_raw"]                     # DataFrame original
                species_col = (src["species_col"] or "").strip()  # Columna de especie escrita por el usuario
                extra_col = src["extra_col"]               # Columna extra que el usuario quiere añadir

                if not species_col:                        # Si no definieron columna de especie
                    st.error(f"Debes indicar la columna de especie para {nombre}.")
                    st.stop()                              # Detengo la app hasta que lo corrijan

                df_clean = limpiar_dataframe(df_raw, species_col, columna_estandar)  # Limpio y estandarizo
                fuentes_limpias[nombre] = df_clean         # Guardo el DataFrame limpio

                if extra_col:                              # Si el usuario pidió una columna extra
                    if extra_col not in df_clean.columns:  # Reviso si existe en el DataFrame limpio
                        st.warning(
                            f"La columna extra '{extra_col}' no se encontró en la fuente {nombre}. "
                            "No se agregará al resultado."
                        )                                  # Si no existe, aviso pero sigo
                    else:
                        extra_cols_map[nombre] = extra_col # La guardo para usarla luego en los merges

            if not fuentes_limpias:                        # Si después de todo no hay fuentes válidas
                st.warning("No se ha cargado ninguna base de datos válida.")
                st.stop()                                  # Detengo el flujo

            # 2. Intersección de especies
            species_sets, tabla_interseccion = construir_interseccion(  # Calculo especies coincidentes
                fuentes_limpias, columna_estandar
            )

            # 3. Agregar columnas extra
            tabla_final = tabla_interseccion.copy()        # Empiezo desde la tabla de intersección

            for nombre_fuente, extra_col in extra_cols_map.items():  # Recorro las fuentes con columna extra válida
                df_src = (
                    fuentes_limpias[nombre_fuente][[columna_estandar, extra_col]]
                    .drop_duplicates(subset=[columna_estandar])      # Quito duplicados por especie
                )
                nuevo_nombre_col = f"{nombre_fuente}_{extra_col}"    # Nombre final de la columna extra

                tabla_final = tabla_final.merge(          # Hago merge para agregar esa columna extra
                    df_src.rename(columns={extra_col: nuevo_nombre_col}),
                    on=columna_estandar,                  # Uno por el nombre científico estándar
                    how="left",                           # Mantengo todas las especies de la intersección
                )

            # 4. Filtro de búsqueda
            df_resultado = tabla_final                    # Empiezo del resultado completo
            if busqueda:                                  # Si el usuario escribió algo en el buscador
                df_resultado = df_resultado[
                    df_resultado[columna_estandar]
                    .str.contains(busqueda, case=False, na=False)  # Filtro por nombre de especie que contenga el texto
                ]

            # 5. Mostrar resultados básicos
            st.markdown(
                '<div class="app-section-title">Resultado: especies coincidentes</div>',  # Título de la sección de resultados
                unsafe_allow_html=True,
            )

            n_inter = len(df_resultado)                   # Número de especies en el resultado filtrado
            st.write(
                f"Se encontraron **{n_inter}** especies coincidentes "
                f"(presentes en al menos 2 fuentes)."
            )

            if n_inter > 0:                               # Si hay al menos una especie
                st.dataframe(df_resultado)                # Muestro la tabla de resultados

                csv_bytes = df_resultado.to_csv(          # Convierto el DataFrame a CSV en memoria
                    index=False,
                    sep=";",                              # Uso punto y coma como separador
                ).encode("utf-8-sig")                     # Codifico en UTF-8 con BOM

                st.download_button(                       # Botón para descargar la tabla como CSV
                    label="💾 Descargar tabla de especies coincidentes (.csv)",
                    data=csv_bytes,
                    file_name="especies_coincidentes.csv",
                    mime="text/csv",
                )

            # ------------------------------------------------------------
            # 6. VISUALIZACIÓN GRÁFICA DE RESULTADOS
            # ------------------------------------------------------------
            if n_inter > 0:                               # Solo tiene sentido graficar si hay resultados
                st.markdown(
                    '<div class="app-section-title">Visualización gráfica de resultados</div>',
                    unsafe_allow_html=True,
                )

                with st.expander("📊 Ver gráficos a partir de la tabla final"):  # Expander para mostrar u ocultar gráficos
                    # 6.1. Especies coincidentes por fuente
                    st.subheader("Especies coincidentes por fuente")

                    coincid_por_fuente = {}               # Diccionario para guardar cuántas especies por fuente
                    for nombre_fuente in species_sets.keys():  # Recorro las fuentes
                        if nombre_fuente in df_resultado.columns:  # Solo si hay columna 0/1 para esa fuente
                            coincid_por_fuente[nombre_fuente] = int(
                                df_resultado[nombre_fuente].sum()  # Sumo los 1 para contar cuántas especies ahí
                            )

                    if coincid_por_fuente:                # Si hay datos para graficar
                        df_plot_fuentes = (
                            pd.DataFrame.from_dict(
                                coincid_por_fuente,
                                orient="index",
                                columns=["Especies coincidentes"],
                            )
                            .sort_values("Especies coincidentes", ascending=False)  # Ordeno de mayor a menor
                        )
                        st.bar_chart(df_plot_fuentes)     # Muestro un gráfico de barras con esas cantidades
                    else:
                        st.write(
                            "No se encontraron columnas de presencia por fuente en la tabla final."
                        )

                    st.markdown("---")                     # Separador dentro del expander

                    # 6.2. Distribución del número de fuentes por especie
                    if "num_fuentes" in df_resultado.columns:  # Reviso que exista la columna num_fuentes
                        st.subheader("Distribución de número de fuentes por especie")

                        conteo_num = (
                            df_resultado["num_fuentes"]
                            .value_counts()
                            .sort_index()                 # Cuento cuántas especies tienen 2, 3, 4 fuentes, etc.
                        )

                        df_hist = conteo_num.reset_index()  # Lo paso a DataFrame
                        df_hist.columns = ["num_fuentes", "n_especies"]  # Renombro columnas

                        st.bar_chart(df_hist.set_index("num_fuentes"))  # Gráfico de barras con num_fuentes en el eje x
                    else:
                        st.write(
                            "La columna 'num_fuentes' no está disponible en la tabla final."
                        )

                    st.markdown("---")                     # Otro separador

                    # 6.3. Columna categórica extra (si existe)
                    st.subheader("Distribución de una columna categórica adicional")

                    cols_candidatas = []                  # Aquí voy a guardar las columnas categóricas posibles
                    columnas_binarias = set(species_sets.keys()) | {
                        "num_fuentes",
                        columna_estandar,
                    }                                     # Columnas que NO quiero usar como categóricas

                    for col in df_resultado.columns:      # Recorro todas las columnas del resultado
                        if col in columnas_binarias:      # Si la columna es binaria o especial la salto
                            continue
                        if df_resultado[col].dtype == "object":  # Solo quiero columnas de texto (categóricas)
                            cols_candidatas.append(col)

                    if cols_candidatas:                   # Si hay columnas categóricas candidatas
                        col_sel = st.selectbox(           # Dejo que el usuario escoja cuál quiere ver
                            "Selecciona una columna categórica para resumir",
                            cols_candidatas,
                        )

                        top_vals = (
                            df_resultado[col_sel]
                            .value_counts()
                            .head(10)                     # Tomo las 10 categorías más frecuentes
                        )

                        st.bar_chart(top_vals)            # Muestro un gráfico de barras con esas categorías
                        st.caption("Se muestran las 10 categorías más frecuentes.")
                    else:
                        st.write(
                            "Por ahora no hay columnas categóricas adicionales para graficar. "
                            "Puedes definir una columna extra en alguna fuente para que aparezca aquí."
                        )

            # ------------------------------------------------------------
            # 7. INDICADORES POR FUENTE
            # ------------------------------------------------------------

            st.markdown(
                '<div class="app-section-title">Indicadores por fuente</div>',  # Título de esta sección
                unsafe_allow_html=True,
            )

            datos_indicadores = []                     # Lista para guardar los indicadores
            for nombre_fuente, conj in species_sets.items():  # Recorro las fuentes y su conjunto de especies
                datos_indicadores.append(
                    {"Fuente": nombre_fuente, "N° especies únicas": len(conj)}  # Guardo cuántas especies únicas hay en cada fuente
                )

            if datos_indicadores:                      # Si tengo indicadores
                df_ind = pd.DataFrame(datos_indicadores)      # Los paso a DataFrame
                st.dataframe(df_ind)                   # Muestro la tabla de indicadores
                st.bar_chart(df_ind.set_index("Fuente")["N° especies únicas"])  # Gráfico de barras con especies únicas por fuente

        except ValueError as e:                        # Si hay un error de valor (por ejemplo formato de datos)
            st.error(f"Ocurrió un problema: {e}")
        except Exception as e:                         # Cualquier otro error inesperado
            st.error(f"Ocurrió un error inesperado: {e}")
else:
    st.info(                                          # Mensaje cuando aún no se ha presionado el botón de procesar
        "Sube tus archivos en las tarjetas superiores, configura las columnas de especie y, si lo deseas, "
        "las columnas extra. Luego pulsa el botón para procesar."
    )

st.markdown("</div>", unsafe_allow_html=True)   # Cierro el contenedor main-card
st.markdown("</div>", unsafe_allow_html=True)   # Cierro el contenedor app-shell
