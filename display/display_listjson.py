import streamlit as st
import numpy as np
import pandas as pd
import streamlit.components.v1 as components
from bs4 import BeautifulSoup

def display_listjson(formato,blocksbyrow=2):
    
    bbr = int(12/blocksbyrow)

    html_stats = ""
    for i in formato:
        html_stats += f"""
        <div class="col-xl-{bbr} col-sm-4 mb-xl-2 mb-4">
          <div class="card">
            <div class="card-body p-3">
              <div class="row">
                <div class="numbers">
                  <h3 class="font-weight-bolder mb-0" style="text-align: center;font-size: 1.5rem;">{i['value']}</h3>
                  <p class="mb-0" style="font-weight: 300;font-size: 1rem;text-align: center;">{i['name']}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        """
    style = """
    <style>
        .tabla_principal {
          max-width: 100%; 
          max-height: 100%; 
        }              
        .impuesto-table {
          overflow-x: auto;
          overflow-y: auto; 
          max-width: 100%; 
          max-height: 400px; 
        }
        .chart-container {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100%;
          width: 100%; 
          margin-top:100px;
        }
        body {
            font-family: Arial, sans-serif;
        }
        
        canvas {
            max-width: 100%;
            max-height: 100%;
            max-height: 300px;
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
    <div class="container-fluid py-1" style="margin-top: 0px;margin-bottom: 50px;">
      <div class="row">
        {html_stats}
      </div>
    </div> 
    </body>
    </html>
    """
    texto = BeautifulSoup(html, 'html.parser')
    st.markdown(texto, unsafe_allow_html=True)
