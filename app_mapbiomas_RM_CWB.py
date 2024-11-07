#%%


#%%
import streamlit as st
import geemap.foliumap as geemap
import ee
import json
import pandas as pd
import plotly.express as px
import geopandas as gpd
import geobr

# Configurar o layout wide
st.set_page_config(layout="wide", page_title="Análise de Uso e Ocupação do solo - MapBiomas")

# Título e descrição do aplicativo
st.title("Análise de Uso e Ocupação do solo")
st.write("""
Este aplicativo permite a visualização interativa da expansão de áreas urbanas e outras classes de uso do solo na Região Metropolitana de Curitiba ao longo dos anos, utilizando dados da Coleção 9 do projeto MapBiomas. Com uma série histórica de 1985 a 2023, o aplicativo oferece a possibilidade de selecionar as classes de interesse e visualizar a evolução temporal.

**Fonte dos dados**: [MapBiomas](https://mapbiomas.org)
""")

# Autenticação com o Google Earth Engine
ee.Initialize()

# Carregar a imagem MapBiomas
mapbiomas_image = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')

# Definir a região de interesse (RM de Curitiba)
gdf_metro = geobr.read_metro_area(year=2018)
gdf_selected_metro = gdf_metro[gdf_metro['name_metro'] == 'RM Curitiba']

# Converter o GeoDataFrame para uma FeatureCollection do Earth Engine
roi = geemap.geopandas_to_ee(gdf_selected_metro)

# Dicionário de classes e cores - Atualizado para incluir apenas as classes visíveis na imagem
dicionario_classes = {
    3: "Formação Florestal",
    9: "Silvicultura",
    11: "Campo Alagado e Área Pantanosa",
    12: "Formação Campestre",
    15: "Pastagem",
    21: "Mosaico de Usos",
    24: "Área Urbanizada",
    25: "Outras Áreas não Vegetadas",
    29: "Afloramento Rochoso",
    30: "Mineração",
    33: "Rio, Lago e Oceano",
    39: "Soja",
    41: "Outras Lavouras Temporárias",
    50: "Restinga Herbácea",
    31: "Aquicultura",
    48: "Outras Lavouras Perenes"
}

# Dicionário de cores correspondente
dicionario_cores = {
    3: "#1f8d49",
    9: "#7a5900",
    11: "#519799",
    12: "#d6bc74",
    15: "#edde8e",
    21: "#ffefc3",
    24: "#d4271e",
    25: "#db4d4f",
    29: "#ffaa5f",
    30: "#9c0027",
    33: "#2532e4",
    39: "#f5b3c8",
    41: "#f54ca9",
    50: "#ad5100",
    31: "#091077",
    48: "#e6ccff"
}

# Seletor de classes - atualizado para permitir a seleção apenas das classes disponíveis na legenda
classes_selecionadas_nomes = st.multiselect("Selecione as classes de interesse", options=list(dicionario_classes.values()), default=['Área Urbanizada'])
classes_selecionadas_codigos = [key for key, value in dicionario_classes.items() if value in classes_selecionadas_nomes]

# Seletor de anos
anos = list(range(1985, 2024))
anos_selecionados = st.multiselect("Selecione o(s) ano(s) (máximo 5 anos)", anos, default=[2023])
if len(anos_selecionados) > 5:
    st.warning("Por favor, selecione no máximo 5 anos.")
    st.stop()

# Criando o mapa com geemap
m = geemap.Map()

# Adicionar as bandas selecionadas ao mapa
for ano in anos_selecionados:
    banda_nome = f'classification_{ano}'
    for classe_codigo in classes_selecionadas_codigos:
        classe_nome = dicionario_classes[classe_codigo]
        classe_cor = dicionario_cores[classe_codigo]
        imagem_classe = mapbiomas_image.select(banda_nome).eq(classe_codigo).selfMask()
        imagem_classe = imagem_classe.clip(roi)
        m.addLayer(imagem_classe, {'palette': [classe_cor], 'min': 1, 'max': 1}, f'{classe_nome} {ano}')

# Adicionar a região de interesse ao mapa
m.addLayer(roi, {}, 'Região Metropolitana de Curitiba')
m.centerObject(roi, zoom=8)

# Exibir o mapa no Streamlit
st.subheader("Mapa Interativo")
m.to_streamlit(height=600)

# Função para calcular a área por classes e anos
@st.cache_data
def calcular_area_por_classes_e_anos(anos, classes_codigos, _roi):
    areas = []
    for ano in anos:
        banda_nome = f'classification_{ano}'
        imagem_ano = mapbiomas_image.select(banda_nome).clip(_roi)
        for classe_codigo in classes_codigos:
            classe_nome = dicionario_classes[classe_codigo]
            # Criar a máscara para a classe e renomear a banda
            imagem_classe = imagem_ano.eq(classe_codigo).selfMask().rename('classe')
            # Calcular a área
            stats = imagem_classe.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=_roi.geometry(),
                scale=30,
                maxPixels=1e13
            )
            # Extrair o valor da área usando o nome da banda 'classe'
            area = stats.getInfo().get('classe', 0) / 1e6  # Converter para km²
            areas.append({'Ano': ano, 'Classe Nome': classe_nome, 'Área (km²)': area})
    df_area = pd.DataFrame(areas)
    return df_area

# Cálculo da área por ano
with st.spinner('Processando...'):
    df_area_selecionados = calcular_area_por_classes_e_anos(anos_selecionados, classes_selecionadas_codigos, roi)
st.success('Processamento concluído!')

# Exibir gráfico de evolução da área
st.subheader(f"Evolução da Área das Classes Selecionadas")

fig = px.line(df_area_selecionados, x='Ano', y='Área (km²)', color='Classe Nome', markers=True, title='Evolução da Área das Classes Selecionadas')

# Atualizar as cores conforme o dicionário de cores
for trace in fig.data:
    classe_nome = trace.name
    classe_codigo = [key for key, value in dicionario_classes.items() if value == classe_nome][0]
    trace.line.color = dicionario_cores[classe_codigo]

st.plotly_chart(fig, use_container_width=True)

# Mostrar tabela de dados
st.dataframe(df_area_selecionados)

# Gráfico de barras com todas as classes (opcional)
if st.checkbox("Mostrar gráfico de barras com todas as classes para os anos selecionados"):
    classes_disponiveis = list(dicionario_classes.values())
    classes_selecionadas_bar = st.multiselect("Selecione as classes a serem incluídas no gráfico", classes_disponiveis, default=classes_disponiveis)

    @st.cache_data
    def calcular_areas_todas_classes(anos_selecionados, _roi):
        dados_areas = []
        for ano in anos_selecionados:
            banda_nome = f'classification_{ano}'
            imagem_ano = mapbiomas_image.select(banda_nome).clip(_roi)
            histograma = imagem_ano.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=_roi.geometry(),
                scale=30,
                maxPixels=1e13
            ).get(banda_nome)
            histograma = ee.Dictionary(histograma).getInfo()
            for classe_codigo_str, contagem in histograma.items():
                classe_codigo = int(classe_codigo_str)
                area_km2 = contagem * (30 * 30) / 1e6  # Cada pixel tem 30x30 metros
                classe_nome = dicionario_classes.get(classe_codigo, 'Desconhecido')
                classe_cor = dicionario_cores.get(classe_codigo, '#000000')
                dados_areas.append({
                    'Ano': ano,
                    'Classe Código': classe_codigo,
                    'Classe Nome': classe_nome,
                    'Área (km²)': area_km2,
                    'Cor': classe_cor
                })
        df_todas_classes = pd.DataFrame(dados_areas)
        return df_todas_classes

    df_todas_classes = calcular_areas_todas_classes(anos_selecionados, roi)
    df_todas_classes = df_todas_classes[df_todas_classes['Classe Nome'].isin(classes_selecionadas_bar)]

    # Gráfico
    st.subheader("Distribuição das Áreas por Classe")
    fig_bar = px.bar(df_todas_classes, x='Ano', y='Área (km²)', color='Classe Nome', barmode='stack', color_discrete_map=dicionario_cores, title='Distribuição das Áreas por Classe')
    st.plotly_chart(fig_bar, use_container_width=True)
    # Mostrar tabela
    st.dataframe(df_todas_classes)
