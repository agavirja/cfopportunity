import streamlit as st
import pandas as pd
import numpy_financial as npf
import json
import streamlit.components.v1 as components
import folium
import geopandas as gpd
import pymysql

from datetime import datetime
from bs4 import BeautifulSoup
from shapely.geometry import Point
from sqlalchemy import create_engine 
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, ColumnsAutoSizeMode, AgGridTheme
from st_aggrid.shared import JsCode

from display.display_listjson import display_listjson
from circle_polygon import circle_polygon

st.set_page_config(layout="wide",page_icon="https://operaciones.fra1.digitaloceanspaces.com/_icons/FAVICON-CF.png",initial_sidebar_state="collapsed")

user     = st.secrets["user_cf_pdfcf"]
password = st.secrets["password_cf_pdfcf"]
host     = st.secrets["host_cf_pdfcf"]
schema   = st.secrets["schema_cf_pdfcf"]

def main():

    #-------------------------------------------------------------------------#
    # Tamano de la pantalla 
    screensize = 1920
    mapwidth   = int(screensize*0.6)
    mapheight  = int(screensize*0.4)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize*0.6)
        mapheight  = int(screensize*0.4)
    except: pass

    col1,col2  = st.columns([3,1],gap="small")
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon':None,
               'reporte':False,
               'data': pd.DataFrame(),
               'geojson_data':None,
               'zoom_start':12,
               'latitud':40.407027,
               'longitud':-3.690974,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
    
    areamin              = 0
    areamax              = 0
    antiguedadmin        = 0
    antiguedadmax        = 0

    #-------------------------------------------------------------------------#
    # Formulario 
    with col2:        
        tipo          = st.selectbox('Tipo de negocio',options=['Rentee','Renta clásica','Uso propio','Flip'])
        preciomin     = st.number_input('Precio mínimo',value=0,min_value=0)
        preciomax     = st.number_input('Precio máximo',value=0,min_value=0)
        obra          = st.toggle('Obra',value=True)
        valorobra     = 0
        if obra:
            valorobra = st.number_input('Valor de obra',value=0,min_value=0)
        areamin       = st.number_input('Área construida mínima',value=0,min_value=0)
        areamax       = st.number_input('Área construida máxima',value=0,min_value=0)
        antiguedadmin = st.number_input('Antigüedad mínima',value=0,min_value=0)
        antiguedadmax = st.number_input('Antigüedad máxima',value=0,min_value=0)
        
    if 'Rentee' in tipo:          codigo = '1'
    elif 'Renta clásica' in tipo: codigo = '2'
    elif 'Flip' in tipo:          codigo = '3'
    elif 'Uso propio' in tipo:    codigo = '4'
    
    #-------------------------------------------------------------------------#
    # Mapa
    with col1:
        m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
        draw = Draw(
                    draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                    edit_options={"poly": {"allowIntersection": False}}
                    )
        draw.add_to(m)
    
        if st.session_state.geojson_data is not None:
            folium.GeoJson(st.session_state.geojson_data, style_function=style_function_comparables).add_to(m)
            
        if not st.session_state.data.empty:
            geopoints = point2geopandas(st.session_state.data.iloc[0:50,:])
            popup     = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geopoints,popup=popup).add_to(m)


        st_map = st_folium(m,width=mapwidth,height=mapheight)
    
        polygonType = ''
        if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
            if st_map['all_drawings']!=[]:
                if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry']:
                    polygonType = st_map['all_drawings'][0]['geometry']['type']
    
        if 'polygon' in polygonType.lower():
            coordenadas                   = st_map['all_drawings'][0]['geometry']['coordinates']
            st.session_state.polygon      = Polygon(coordenadas[0])
            st.session_state.geojson_data = mapping(st.session_state.polygon)
            polygon_shape                 = shape(st.session_state.geojson_data)
            centroid                      = polygon_shape.centroid
            st.session_state.latitud      = centroid.y
            st.session_state.longitud     = centroid.x
            st.session_state.zoom_start   = 15
            st.rerun()

    inputvar = {
        'tipo':tipo,
        'preciomin':preciomin,
        'preciomax':preciomax,
        'obra':obra,
        'valorobra':valorobra,
        'areamin':areamin,
        'areamax':areamax,
        'antiguedadmin':antiguedadmin,
        'antiguedadmax':antiguedadmax,
        }

    if st.session_state.polygon is not None:        
        inputvar['polygon'] = str(st.session_state.polygon)
        with col2:
            st.write('')
            st.write('')
            st.write('')
            st.write('')
            if st.button('Buscar'):
                st.cache_data.clear()
                st.session_state.reporte = True
                st.rerun()

        with col2:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()

    if st.session_state.reporte:
        with st.spinner('Buscando data'):
            data     = getdataoportunidades(inputvar,polygon=str(st.session_state.polygon))
            datapaso = pd.DataFrame()
        if not data.empty:
            if 'Rentee' in tipo:
                datapaso = data[data['caprate_habitaciones_+2']>0]
                datapaso = datapaso.sort_values(by='caprate_habitaciones_+2',ascending=False)
            elif 'Renta clásica' in tipo:
                datapaso = data[data['forecast_precio_renta']>0]
                datapaso = datapaso.sort_values(by='caprate',ascending=False)
            elif 'Flip' in tipo:
                datapaso = data[data['forecast_precio_venta']>0]
                if not datapaso.empty:
                    datapaso['diferencia'] = abs(datapaso['forecast_precio_venta']-datapaso['precio'])/datapaso['precio']
                    datapaso               = datapaso[datapaso['diferencia']<0.2]
                    datapaso               = datapaso[datapaso['precio']<datapaso['forecast_precio_venta']]
                    datapaso               = datapaso.sort_values(by='diferencia',ascending=False)
            elif 'Uso propio' in tipo:
                datapaso = data[data['precio']>0]
                datapaso['diferencia'] = abs(datapaso['forecast_precio_venta']-datapaso['precio'])
                datapaso = datapaso.sort_values(by='diferencia',ascending=True)
        st.session_state.data    = datapaso.copy()
        st.session_state.reporte = False
        st.rerun()
  
    latitud,longitud = None,None
    if 'last_object_clicked' in st_map and st_map['last_object_clicked']:
        latitud  = st_map['last_object_clicked']['lat']
        longitud = st_map['last_object_clicked']['lng']
        
    datacomparables = pd.DataFrame()
    if longitud is not None and latitud is not None:
        idd = (st.session_state.data['latitud']==latitud) & (st.session_state.data['longitud']==longitud)
        if sum(idd)>0:
            datacomparables = st.session_state.data[idd]
            
    datalistacomparables = pd.DataFrame()
    if not datacomparables.empty:
        if 'Rentee' in tipo:
            idcodigos = datacomparables['id_compraracion_habitaciones'].iloc[0].split('|')
        elif 'Renta clásica' in tipo:
            idcodigos = datacomparables['id_compraracion_renta'].iloc[0].split('|')
        elif 'Flip' in tipo:
            idcodigos = datacomparables['id_compraracion_venta'].iloc[0].split('|')
        elif 'Uso propio' in tipo:
            idcodigos = datacomparables['id_compraracion_venta'].iloc[0].split('|')
        with st.spinner('Buscando data de comparables'):
            datalistacomparables = getdatacomparacion(idcodigos)  


    #-------------------------------------------------------------------------#
    # Comparables
    #-------------------------------------------------------------------------#
    if not datalistacomparables.empty:
        st.write('Mapa de inmuebles que se utilziaron apra la comparacion')
        col1,col2 = st.columns([0.6,0.4])
        roundpol = circle_polygon(300,latitud,longitud)
        m        = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
        folium.GeoJson(roundpol, style_function=style_function_comparables).add_to(m)
        if not st.session_state.data.empty:
            geopoints = point2geopandas2(datalistacomparables)
            popup     = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geopoints,popup=popup).add_to(m)
        with col1:
            st_map = st_folium(m,width=1000,height=500)
        
        html = tabla_comparables(datalistacomparables)
        #texto = BeautifulSoup(html, 'html.parser')
        #st.markdown(texto, unsafe_allow_html=True)
        with col2:
            st.components.v1.html(html,height=500,scrolling=True)

    #-------------------------------------------------------------------------#
    # Tabla de oportundiades
    #-------------------------------------------------------------------------#
    datasavedlist = getsavedlist(codigo)
    if not datasavedlist.empty:
        #with st.expander('Tabla de oportunidades guardadas', expanded=False):
        st.write('Oportunidades guardadas')
        variables = [x for x in ['id_inmueble','created_at','barrio','precio','area','habitaciones','banos','numero_piso','garaje','url_activo'] if x in datasavedlist]
        df = datasavedlist.copy()
        df = df[variables]
        df.rename(columns={'url_activo':'link','created_at':'fecha de creacion'},inplace=True)
        
        gb = GridOptionsBuilder.from_dataframe(df,editable=True)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        cell_renderer =  JsCode("""function(params) {return `<a href=${params.value} target="_blank">${params.value}</a>`}""")
        
        gb.configure_column(
            "link",
            headerName="link",
            width=100,
            cellRenderer=JsCode("""
                class UrlCellRenderer {
                  init(params) {
                    this.eGui = document.createElement('a');
                    this.eGui.innerText = 'Link';
                    this.eGui.setAttribute('href', params.value);
                    this.eGui.setAttribute('style', "text-decoration:none");
                    this.eGui.setAttribute('target', "_blank");
                  }
                  getGui() {
                    return this.eGui;
                  }
                }
            """)
        )
        
        response = AgGrid(df,
                    gridOptions=gb.build(),
                    columns_auto_size_mode="FIT_CONTENTS",
                    theme=AgGridTheme.STREAMLIT,
                    updateMode=GridUpdateMode.VALUE_CHANGED,
                    allow_unsafe_jscode=True)
        
        df = pd.DataFrame(response['selected_rows'])
        if not df.empty:  
            df = df[['id_inmueble']]
            df['codigo'] = codigo
            col1, col2 = st.columns(2)
            with col1:
                if st.button('Eliminar',key='guardar_oportunidades'):
                    with st.spinner('Guardando'):
                        updatetable(df)
                        st.session_state.show = False
                        st.session_state.polygonfilter = None
                        st.cache_data.clear()
                        st.rerun()
                     
                        
    #---------------------------------------------------------------------#
    # Guardad oportundiades
    #---------------------------------------------------------------------#
    if not st.session_state.data.empty:
        #with st.expander('Lista de oportundiades para guardar', expanded=False):
        st.write('Lista de oportunidades')
        variables = [x for x in ['id_inmueble','barrio','precio','area','habitaciones','banos','numero_piso','garaje','url_activo'] if x in st.session_state.data]
        df = st.session_state.data.copy()
        col1, col2 = st.columns(2)
        with col1:
            options  = ['Todos']+list(sorted(df['id_inmueble'].unique()))
            selectid = st.selectbox('Filtrar por ID:',options=options)
            if 'Todos' not in str(selectid):
                df = df[df['id_inmueble']==selectid]

        df = df[variables]
        df.rename(columns={'url_activo':'link'},inplace=True)
        
        gb = GridOptionsBuilder.from_dataframe(df,editable=True)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        cell_renderer =  JsCode("""function(params) {return `<a href=${params.value} target="_blank">${params.value}</a>`}""")
        
        gb.configure_column(
            "link",
            headerName="link",
            width=100,
            cellRenderer=JsCode("""
                class UrlCellRenderer {
                  init(params) {
                    this.eGui = document.createElement('a');
                    this.eGui.innerText = 'Link';
                    this.eGui.setAttribute('href', params.value);
                    this.eGui.setAttribute('style', "text-decoration:none");
                    this.eGui.setAttribute('target', "_blank");
                  }
                  getGui() {
                    return this.eGui;
                  }
                }
            """)
        )
        
        response = AgGrid(df,
                    gridOptions=gb.build(),
                    height=400,
                    columns_auto_size_mode="FIT_CONTENTS",
                    theme=AgGridTheme.STREAMLIT,
                    updateMode=GridUpdateMode.VALUE_CHANGED,
                    allow_unsafe_jscode=True)
    
        df = pd.DataFrame(response['selected_rows'])
        if not df.empty:  
            df = pd.DataFrame(response['selected_rows'])
            if '_selectedRowNodeInfo' in df: del df['_selectedRowNodeInfo']
            idd = st.session_state.data['id_inmueble'].isin(df['id_inmueble'])
            data2export = st.session_state.data[idd]
            
            data2export['codigo']     = codigo
            data2export['created_at'] = datetime.now().strftime('%Y-%m-%d')
            data2export['updated_at'] = datetime.now().strftime('%Y-%m-%d')
            data2export['activo']     = 1
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button('Guardar',key='guardar_oportunidades'):
                    with st.spinner('Guardando'):
                        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}') 
                        data2export.to_sql('data_oportunidades_byproducto', engine, if_exists='append', index=False, chunksize=1)
                        st.success('Oportundiades guardadas exitosamente')
                        engine.dispose()
                        st.session_state.show = False
                        st.session_state.polygonfilter = None
                        st.cache_data.clear()
                        st.rerun()
                
    #---------------------------------------------------------------------#
    # Mostrar todas las oportundiades
    #---------------------------------------------------------------------#

    if not st.session_state.data.empty:
        css_format = """
            <style>
              .property-image {
                width: 100%;
            	   height: 250px;
            	   overflow: hidden; 
                margin-bottom: 10px;
              }
              .price-info {
                font-family: 'Roboto', sans-serif;
                font-size: 20px;
                margin-bottom: 2px;
                text-align: center;
              }
              .caracteristicas-info {
                font-family: 'Roboto', sans-serif;
                font-size: 12px;
                margin-bottom: 2px;
                text-align: center;
              }
              img{
                max-width: 100%;
                width: 100%;
                height:100%;
                object-fit: cover;
                margin-bottom: 10px; 
              }
            </style>
        """
        
        imagenes = ''
        for i, inmueble in st.session_state.data.iterrows():
            addtitle = ""
            if 'Rentee' in tipo:
                try:    renthab1 = f"""<p class="caracteristicas-info"><b>Hab +1: ${inmueble['rent_habitaciones_+1']:,.0f}  - caprate: {"{:.2f}%".format(inmueble['caprate_habitaciones_+1']*100)}</p>"""
                except: renthab1 = ""
                try:    renthab2 = f"""<p class="caracteristicas-info"><b>Hab +2: ${inmueble['rent_habitaciones_+2']:,.0f}  - caprate: {"{:.2f}%".format(inmueble['caprate_habitaciones_+2']*100)}</p>"""
                except: renthab2 = ""
                addtitle = f"""
                {renthab1}
                {renthab2}
                """
            elif 'Renta clásica' in tipo:
                try:    rentforecast = f"""<p class="caracteristicas-info"><b>Renta estimada: ${inmueble['forecast_precio_renta']:,.0f}  - caprate: {"{:.2f}%".format(inmueble['caprate']*100)}</p>"""
                except: rentforecast = ""
                addtitle = f"""
                {rentforecast}
                """
            elif 'Flip' in tipo:
                try:    sellforecast = f"""<p class="caracteristicas-info"><b>Sell Forecast: ${inmueble['forecast_precio_venta']:,.0f}  - diferencia: {"{:.2f}%".format(inmueble['diferencia']*100)}</p>"""
                except: sellforecast = ""
                addtitle = f"""
                {sellforecast}
                """         
            elif 'Uso propio' in tipo:
                addtitle = ""
            
            caracteristicas = f'<strong>{inmueble["area"]}</strong> mt<sup>2</sup> | <strong>{int(inmueble["habitaciones"])}</strong> hab | <strong>{int(inmueble["banos"])}</strong> baños'
            imagenes += f'''
            <div class="col-xl-3 col-sm-6 mb-xl-2 mb-2">
              <div class="card h-100">
                <div class="card-body p-3">
                    <a href="{inmueble['url_activo']}" target="_blank">
                    <div class="property-image">
                        <img src="{inmueble['url_img1']}"  alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                    </div>
                    </a>
                  <p class="price-info"><b>${inmueble['precio']:,.0f}</b></h3>
                  <p class="caracteristicas-info"><b>Id: {inmueble['id_inmueble']}</b></h3>
                  <p class="caracteristicas-info">{caracteristicas}</p>
                  {addtitle}
                </div>
              </div>
            </div>            
            '''
        texto = f"""
            <!DOCTYPE html>
            <html>
              <head>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet"/>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet"/>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" id="pagestyle" rel="stylesheet"/>
              {css_format}
              </head>
              <body>
              <div class="container-fluid py-4">
                <div class="row">
                {imagenes}
                </div>
              </div>
              </body>
            </html>
            """
        texto = BeautifulSoup(texto, 'html.parser')
        st.markdown(texto, unsafe_allow_html=True)

def style_function_comparables(feature):
    return {
        'fillColor': '#0095ff',
        'color': 'blue',
        'weight': 0,
    }

@st.cache_data(show_spinner=False)
def getdataoportunidades(inputvar,polygon=None):
    if isinstance(polygon, str) and polygon!='' and not 'none' in polygon.lower():
        dataoportundiades = datamarket(inputvar,polygon=polygon)
    else:
        dataoportundiades = datamarket(inputvar,polygon=None)

    dataoportundiades = dataoportundiades.iloc[0:100,:]
    return dataoportundiades
    
@st.cache_data(show_spinner=False)
def datamarket(inputvar,polygon=None):

    preciomin = inputvar['preciomin'] if 'preciomin' in inputvar and (isinstance(inputvar['preciomin'], float) or isinstance(inputvar['preciomin'], int)) else None
    preciomax = inputvar['preciomax'] if 'preciomax' in inputvar and (isinstance(inputvar['preciomax'], float) or isinstance(inputvar['preciomax'], int)) else None
    areamin   = inputvar['areamin'] if 'areamin' in inputvar and (isinstance(inputvar['areamin'], float) or isinstance(inputvar['areamin'], int)) else 0
    areamax   = inputvar['areamax'] if 'areamax' in inputvar and (isinstance(inputvar['areamax'], float) or isinstance(inputvar['areamax'], int)) else 0
    
    query = ""
    if isinstance(polygon, str):
        query += f" AND ST_CONTAINS(ST_GEOMFROMTEXT('{polygon}'), POINT(`longitud`,`latitud`))"
    
    if preciomin>0:
        query += f" AND precio>={preciomin}"
    if preciomax>0:
        query += f" AND precio<={preciomax}"
    if areamin>0:
        query += f" AND area>={areamin}"
    if areamax>0:
        query += f" AND area<={areamax}"
     
    if query!="":
        query = query.strip().strip('AND')
        query = f' WHERE {query} '
            
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data   = pd.read_sql_query(f"SELECT * FROM {schema}.data_caprate_idealista {query}" , engine)
    engine.dispose()
    data.index = range(len(data))
    
    return data

# forecast_precio_renta/precio
@st.cache_data(show_spinner=False)
def dataidcodigos(codigos):
    data  = pd.DataFrame()
    if isinstance(codigos, list):
        query = ','.join(codigos)
        query = f" WHERE id_inmueble IN ({query})"  
        
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data   = pd.read_sql_query(f"SELECT * FROM {schema}.data_idealista {query}" , engine) 
        engine.dispose()

    return data

@st.cache_data(show_spinner=False)
def point2geopandas(data):
    
    geojson = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        
        data['popup'] = None
        data.index    = range(len(data))
        img_style = '''
        <style>               
            .property-image{
              flex: 1;
            }
            img{
                width:200px;
                height:120px;
                object-fit: cover;
                margin-bottom: 2px; 
            }
        </style>
                '''
        for idd,items in data.iterrows():
            try:    precio = f"<b> Precio:</b> ${items['precio']:,.0f}<br>"
            except: precio = "<b> Empresa:</b> Sin información <br>" 
            try:    area = f"<b> Área:</b> {items['area']}<br>"
            except: area = "<b> Área:</b> Sin información <br>" 
            
            try:    habitaciones = f"<b> Habitaciones:</b> {int(items['habitaciones'])}<br>"
            except: habitaciones = "<b> Habitaciones:</b> Sin información <br>" 
            try:    banos = f"<b> Baños:</b> {int(items['banos'])}<br>"
            except: banos = "<b> Baños:</b> Sin información <br>"     
            try:    garajes = f"<b> Garajes:</b> {int(items['garaje'])}<br>"
            except: garajes = "<b> Garajes:</b> Sin información <br>"                 
            try:    ascensor = f"<b> Ascensor:</b> {items['ascensor']}<br>"
            except: ascensor = "<b> Ascensor:</b> Sin información <br>"  
            try:    barrio = f"<b> Barrio:</b> {items['barrio']}<br>"
            except: barrio = "<b> Barrio:</b> Sin información <br>" 
            try:    numeropiso = f"<b> Planta:</b> {items['numero_piso']}<br>"
            except: numeropiso = "<b> Planta:</b> Sin información <br>"
            try:    url = f"""<b> url:</b> <a href="{items['url_activo']}" target="_blank" style="color: black;">{items['url_activo']}</a>"""
            except: url = "<b> url:</b> Sin información <br>"    
            #                         <a href="http://localhost:8501/Dashboard_ofertas?idinmueble={items['id_inmueble']}" target="_blank" style="color: black;">

            popup_content =  f'''
            <!DOCTYPE html>
            <head>
              {img_style}
            </head>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                        <a href="{items['url_activo']}" target="_blank" style="color: black;">
                            <div class="property-image">
                                <img src="{items['url_img1']}"  alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                            </div>
                            {barrio}
                            {precio}
                            {area}
                            {habitaciones}
                            {banos}
                            {garajes}
                            {numeropiso}
                            {ascensor}
                        </a>
                    </div>
                    {url}
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        data    = data[['popup','geometry']]
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def point2geopandas2(data):
    
    geojson = pd.DataFrame().to_json()
    if 'ad_latitude' in data and 'ad_longitude' in data:
        data = data[(data['ad_latitude'].notnull()) & (data['ad_longitude'].notnull())]
    if not data.empty:
        data['geometry'] = data.apply(lambda x: Point(x['ad_longitude'],x['ad_latitude']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        
        data['popup'] = None
        data.index    = range(len(data))
        img_style = '''
        <style>               
            .property-image{
              flex: 1;
            }
            img{
                width:200px;
                height:120px;
                object-fit: cover;
                margin-bottom: 2px; 
            }
        </style>
                '''
        for idd,items in data.iterrows():
            try:    precio = f"<b> Precio:</b> ${items['ad_price']:,.0f}<br>"
            except: precio = "<b> Empresa:</b> Sin información <br>" 
            try:    area = f"<b> Área:</b> {items['ad_area']}<br>"
            except: area = "<b> Área:</b> Sin información <br>" 
            
            try:    habitaciones = f"<b> Habitaciones:</b> {int(items['ad_roomnumber'])}<br>"
            except: habitaciones = "<b> Habitaciones:</b> Sin información <br>" 
            try:    banos = f"<b> Baños:</b> {int(items['ad_bathnumber'])}<br>"
            except: banos = "<b> Baños:</b> Sin información <br>"     
            try:    url = f"""<b> url:</b> <a href="{items['ad_urlactive']}" target="_blank" style="color: black;">{items['url_activo']}</a>"""
            except: url = "<b> url:</b> Sin información <br>"    
            popup_content =  f'''
            <!DOCTYPE html>
            <head>
              {img_style}
            </head>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                        <a href="{items['ad_urlactive']}" target="_blank" style="color: black;">
                            <div class="property-image">
                                <img src="{items['ad_urlimg1']}"  alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                            </div>
                            {precio}
                            {area}
                            {habitaciones}
                            {banos}
                        </a>
                    </div>
                    {url}
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        data    = data[['popup','geometry']]
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def getdatacomparacion(codigos):
    data = pd.DataFrame()
    if isinstance(codigos, list):
        lista  = "','".join(codigos)
        query  = f" ad_id IN ('{lista}')"
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data   = pd.read_sql_query(f"SELECT * FROM {schema}.datascraping_bruta_paso1 WHERE {query}" , engine)
        engine.dispose()
    return data
    
@st.cache_data(show_spinner=False)
def getsavedlist(codigo):
    data = pd.DataFrame()
    if codigo is not None:
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data   = pd.read_sql_query(f"SELECT * FROM {schema}.data_oportunidades_byproducto WHERE codigo = '{codigo}' AND activo=1" , engine)
        engine.dispose()
    return data
    
def updatetable(datachange):
    conn = pymysql.connect(host=host,
                   user=user,
                   password=password,
                   db=schema)
    with conn.cursor() as cursor:
        sql = "UPDATE pdfcf.data_oportunidades_byproducto SET activo=0  WHERE id_inmueble=%s AND codigo=%s "
        list_of_tuples = datachange.to_records(index=False).tolist()
        cursor.executemany(sql, list_of_tuples)
    conn.commit()
    conn.close() 
    
@st.cache_data(show_spinner=False)
def principal_table(datainfo=pd.DataFrame()):
    
    tabladescripcion = ""
    if not datainfo.empty:
        html_tabla_paso = ""
        conteo    = 0
        for s in range(len(datainfo)):
            html_paso = ""
            try:    usosuelo = datainfo['usosuelo'].iloc[s]
            except: usosuelo = None
            try:    predios  = int(datainfo['predios'].iloc[s])
            except: predios  = None
            try:    areamedian = int(datainfo['areamedian'].iloc[s])
            except: areamedian = None
            try:    transacciones  = int(datainfo['transacciones'].iloc[s])
            except: transacciones  = None
            try:    valormt2trans  = f"${datainfo['valormt2_transacciones'].iloc[s]:,.0f} m²" if pd.notnull(datainfo['valormt2_transacciones'].iloc[s]) else None
            except: valormt2trans  = None
            
            formato   = {'Transacciones (último año):':transacciones,'Valor promedio transacciones (último año):':valormt2trans,'# Predios (matrículas independientes):':predios,'Área construida promedio:':areamedian}
            for key,value in formato.items():
                if value is not None:
                    html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
     
            if html_paso!="":
                titulo = f"""<tr><td style="border: none;margin-bottom:30px;"><h6 class="mb-0 text-sm" style="color: #000;margin-bottom:30px;">{usosuelo}:</h6></td>"""
                spaces = ""
                if conteo>0:
                    spaces = """<tr><td style="border: none;">&nbsp</td></tr>"""
                conteo += 1
                html_tabla_paso += f"""
                {spaces}
                {titulo}
                {html_paso}
                """
                
        if html_tabla_paso!="":
            tabladescripcion = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Información General</td></tr>{html_tabla_paso}</tbody></table></div>"""
            tabladescripcion = f"""<div class="col-md-12">{tabladescripcion}</div>"""

    style = """
    <style>
        .css-table {
            overflow-x: auto;
            overflow-y: auto;
            width: 100%;
            height: 100%;
        }
        .css-table table {
            width: 100%;
            padding: 0;
        }
        .css-table td {
            text-align: left;
            padding: 0;
        }
        .css-table h6 {
            line-height: 1; 
            font-size: 50px;
            padding: 0;
        }
        .css-table td[colspan="labelsection"] {
          text-align: left;
          font-size: 15px;
          color: #6EA4EE;
          font-weight: bold;
          border: none;
          border-bottom: 2px solid #6EA4EE;
          margin-top: 20px;
          display: block;
          font-family: 'Inter';
        }
        .css-table td[colspan="labelsectionborder"] {
          text-align: left;
          border: none;
          border-bottom: 2px solid blue;
          margin-top: 20px;
          display: block;
          padding: 0;
        }
        
        #top {
            position: absolute;
            top: 0;
        }
        
        #top:target::before {
            content: '';
            display: block;
            height: 100px; 
            margin-top: -100px; 
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
      <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
      <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      {style}
    </head>
    <body>
      <div class="container-fluid py-4" style="margin-bottom: 0px;margin-top: 0px;">
        <div class="row">
          <div class="col-md-12 mb-md-0 mb-2">
            <div class="card h-100">
              <div class="card-body p-3">
                <div class="container-fluid py-4">
                  <div class="row" style="margin-bottom: 0px;margin-top: 0px;">
                    {tabladescripcion}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    return html


def tabla_comparables(datalistacomparables):

    html = ""
    if not datalistacomparables.empty:
        num_comparables = len(datalistacomparables)
        precio          = f"${datalistacomparables['ad_price'].median():,.0f}"
        moda_hab        = datalistacomparables['ad_roomnumber'].mode()
        moda_banos      = datalistacomparables['ad_bathnumber'].mode()
        formato         = {'Número de comparables:':num_comparables,'Precio promedio':precio,'Moda de número de habitaciones':moda_hab.iloc[0],'Moda de número de baños':moda_banos.iloc[0]}
        
        html_paso = ""
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
        if html_paso!="":
            tablacomplementaria = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Descripción</td></tr>{html_paso}</tbody></table></div>"""
            tablacomplementaria = f"""<div class="col-md-6">{tablacomplementaria}</div>"""
                       
                
        style = """
        <style>
            .css-table {
                overflow-x: auto;
                overflow-y: auto;
                width: 100%;
                height: 100%;
            }
            .css-table table {
                width: 100%;
                padding: 0;
            }
            .css-table td {
                text-align: left;
                padding: 0;
            }
            .css-table h6 {
                line-height: 1; 
                font-size: 50px;
                padding: 0;
            }
            .css-table td[colspan="labelsection"] {
              text-align: left;
              font-size: 15px;
              color: #6EA4EE;
              font-weight: bold;
              border: none;
              border-bottom: 2px solid #6EA4EE;
              margin-top: 20px;
              display: block;
              font-family: 'Inter';
            }
            .css-table td[colspan="labelsectionborder"] {
              text-align: left;
              border: none;
              border-bottom: 2px solid blue;
              margin-top: 20px;
              display: block;
              padding: 0;
            }
            
            #top {
                position: absolute;
                top: 0;
            }
            
            #top:target::before {
                content: '';
                display: block;
                height: 100px; 
                margin-top: -100px; 
            }
        </style>
        """
        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
          <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
          <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
          <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          {style}
        </head>
        <body>
          <div class="container-fluid py-4" style="margin-bottom: 0px;margin-top: -50px;">
            <div class="row">
              <div class="col-md-12 mb-md-0 mb-2">
                <div class="card h-100">
                  <div class="card-body p-3">
                    <div class="container-fluid py-4">
                      <div class="row" style="margin-bottom: 0px;margin-top: 0px;">
                        {tablacomplementaria}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </body>
        </html>
        """
    return html

if __name__ == "__main__":
    main()
    components.html(
        """
    <script>
    const elements = window.parent.document.querySelectorAll('.stButton button')
    elements[0].style.backgroundColor = '#B98C65';
    elements[0].style.fontWeight = 'bold';
    elements[0].style.color = 'white';
    elements[0].style.width = '100%';

    elements[1].style.backgroundColor = '#B4B9C0';
    elements[1].style.fontWeight = 'bold';
    elements[1].style.color = 'white';
    elements[1].style.width = '100%';

    elements[2].style.backgroundColor = '#B98C65';
    elements[2].style.fontWeight = 'bold';
    elements[2].style.color = 'white';
    elements[2].style.width = '100%';

    </script>
    """
    )