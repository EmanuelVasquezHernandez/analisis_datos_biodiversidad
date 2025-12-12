"""
utils.py
Funciones de apoyo para la app BioData Manager:
- leer_archivo_subido
- limpiar_dataframe
- construir_interseccion
"""

import pandas as pd  # Uso pandas para manejar todas las tablas de datos


def leer_archivo_subido(file):
    """
    Lee un archivo subido desde Streamlit (CSV o Excel) y lo convierte en un DataFrame.
    :param file: objeto devuelto por st.file_uploader
    :return: pandas.DataFrame o None si no hay archivo
    """
    if file is None:
        # Si el usuario no ha subido nada, no tengo nada que leer
        return None

    # Tomo el nombre del archivo para saber su extensión
    nombre = file.name
    extension = nombre.split(".")[-1].lower()  # Me quedo con lo que hay después del último punto

    # Si el archivo es CSV
    if extension == "csv":
        # Leo el CSV; sep=None deja que pandas intente adivinar el separador
        df = pd.read_csv(file, sep=None, engine="python")
        return df

    # Si el archivo es Excel (xls o xlsx)
    if extension in ("xls", "xlsx"):
        # Leo el archivo de Excel
        df = pd.read_excel(file)
        return df

    # Si llega aquí, es un tipo de archivo que no estoy manejando
    raise ValueError(
        f"Formato de archivo no soportado: {extension}. Usa CSV o Excel."
    )


def limpiar_dataframe(df, columna_especie_original, columna_estandar):
    """
    Limpia y estandariza un DataFrame para que:
    - Tenga una columna con el nombre científico estandarizado (columna_estandar).
    - Elimine filas sin nombre de especie.
    - Elimine duplicados por especie.
    - Normalice el texto (espacios, mayúsculas/minúsculas).

    :param df: DataFrame original
    :param columna_especie_original: nombre de la columna de especie en ese DataFrame
    :param columna_estandar: nombre que queremos usar de forma estándar (ej. 'scientificName')
    :return: DataFrame limpio
    """

    # Primero verifico que la columna de especie original exista
    if columna_especie_original not in df.columns:
        raise ValueError(
            f"La columna '{columna_especie_original}' no existe en el archivo."
        )

    # Hago una copia para no modificar el DataFrame original directamente
    df_clean = df.copy()

    # Renombro la columna de especie original al nombre estándar que usará toda la app
    df_clean = df_clean.rename(
        columns={columna_especie_original: columna_estandar}
    )

    # Normalizo la columna de especie:
    # - Me aseguro que sea string
    # - Quito espacios sobrantes al inicio y al final
    df_clean[columna_estandar] = (
        df_clean[columna_estandar]
        .astype(str)   # Convierto todo a texto
        .str.strip()   # Quito espacios al principio y al final
    )

    # Elimino filas donde la especie haya quedado vacía
    df_clean = df_clean[df_clean[columna_estandar] != ""]

    # Paso todo a minúsculas para comparar nombres sin problemas de mayúsculas/minúsculas
    df_clean[columna_estandar] = df_clean[columna_estandar].str.lower()

    # Elimino duplicados por nombre de especie dentro de esta fuente
    df_clean = df_clean.drop_duplicates(subset=[columna_estandar])

    # Devuelvo el DataFrame limpio y estandarizado
    return df_clean


def construir_interseccion(fuentes_limpias, columna_estandar):
    """
    Construye:
    - Un diccionario con el conjunto de especies únicas por fuente.
    - Una tabla que indica, para cada especie presente en AL MENOS 2 fuentes,
      en cuáles aparece y cuántas fuentes la reportan.

    :param fuentes_limpias: dict {nombre_fuente: DataFrame_limpio}
    :param columna_estandar: nombre de la columna de especie estándar (ej. 'scientificName')
    :return:
        species_sets: dict {nombre_fuente: set(especies)}
        tabla_interseccion: DataFrame con columnas:
            - columna_estandar
            - nombre_fuente (0/1 si aparece o no)
            - num_fuentes (cuántas fuentes la contienen)
    """

    # Aquí voy a guardar, para cada fuente, el conjunto de especies únicas
    species_sets = {}

    # Recorro cada fuente y su DataFrame limpio
    for nombre_fuente, df in fuentes_limpias.items():
        # Tomo la columna de especie, elimino nulos y saco los valores únicos
        especies = set(
            df[columna_estandar]
            .dropna()
            .unique()
        )
        # Guardo el conjunto de especies para esta fuente
        species_sets[nombre_fuente] = especies

    # Si no hay ninguna fuente, devuelvo estructuras vacías
    if not species_sets:
        return {}, pd.DataFrame(columns=[columna_estandar])

    # Aquí construyo la unión de todas las especies de todas las fuentes
    all_species = set()
    for conj in species_sets.values():
        all_species |= conj  # Operación de unión de conjuntos

    # En esta lista voy a ir armando las filas de la tabla final
    filas = []
    # Recorro cada especie que apareció en al menos una fuente
    for especie in all_species:
        # Creo un diccionario que indica si la especie está (True/False) en cada fuente
        presencia = {
            nombre_fuente: (especie in conj)
            for nombre_fuente, conj in species_sets.items()
        }

        # Cuento en cuántas fuentes aparece esta especie
        num_fuentes = sum(presencia.values())

        # Solo me interesan las especies que están en 2 o más bases
        if num_fuentes >= 2:
            # Empiezo a armar la fila con el nombre científico y num_fuentes
            fila = {
                columna_estandar: especie,
                "num_fuentes": num_fuentes,
            }
            # Para cada fuente, guardo 1 si está, 0 si no está
            for nombre_fuente, presente in presencia.items():
                fila[nombre_fuente] = 1 if presente else 0

            # Agrego la fila a la lista de filas
            filas.append(fila)

    # Convierto la lista de diccionarios (filas) en un DataFrame
    tabla_interseccion = pd.DataFrame(filas)

    # Si la tabla no está vacía, la ordeno:
    # primero por num_fuentes (de mayor a menor) y luego por nombre científico
    if not tabla_interseccion.empty:
        tabla_interseccion = tabla_interseccion.sort_values(
            by=["num_fuentes", columna_estandar],
            ascending=[False, True],
        ).reset_index(drop=True)

    # Devuelvo:
    # - species_sets: conjuntos de especies por fuente
    # - tabla_interseccion: tabla de especies presentes en >= 2 fuentes
    return species_sets, tabla_interseccion
