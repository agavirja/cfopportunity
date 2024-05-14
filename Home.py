import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide",page_icon="https://operaciones.fra1.digitaloceanspaces.com/_icons/FAVICON-CF.png")

# streamlit run D:\Dropbox\Empresa\CapitalFriend\ProyectoOportunidades\_APP\Home.py
# https://streamlit.io/
# pipreqs --encoding utf-8 "D:\Dropbox\Empresa\CapitalFriend\ProyectoCostumerJourney\Operaciones\_APP"

#------------#
# Powersheel #

# Archivos donde esta la palabra "urbextestapp\.streamlit\.app" o "urbextestapp\.streamlit\.app"
# Get-ChildItem -Path D:\Dropbox\Empresa\CapitalFriend\ProyectoCostumerJourney\Operaciones\_APP -Recurse -Filter *.py | ForEach-Object { if (Get-Content $_.FullName | Select-String -Pattern 'localhost:8501' -Quiet) { $_.FullName } }

# Reemplazar "urbextestapp.streamlit.app" por "localhost:8501" o al reves en los archivos donde esta la palabra
# Get-ChildItem -Path D:\Dropbox\Empresa\CapitalFriend\ProyectoCostumerJourney\Operaciones\_APP -Recurse -Filter *.py | ForEach-Object {(Get-Content $_.FullName) | ForEach-Object {$_ -replace 'https://operaciones.streamlit.app', 'https://operaciones.streamlit.app'} | Set-Content $_.FullName}




