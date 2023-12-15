#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import requests
from requests.auth import HTTPDigestAuth
import subprocess
import time
import json
import sys
import termios
import tty

debug = True

# Ruta al archivo de configuración
CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), "tvheadend_config.json")

def obtener_configuracion_tvheadend():
    # Verificar si existe un archivo de configuración previo
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as file:
            config = json.load(file)
    else:
        # Si no hay un archivo de configuración, solicitar la configuración al usuario
        config = {
            "TVHEADEND_IP": input("Ingrese la dirección IP y el puerto de TVHeadend: "),
            "TVHEADEND_USERNAME": input("Ingrese el nombre de usuario de TVHeadend: "),
            "TVHEADEND_PASSWORD": input("Ingrese la contraseña de TVHeadend: "),
        }

        # Guardar la configuración en el archivo
        with open(CONFIG_FILE_PATH, "w") as file:
            json.dump(config, file, indent=2)

    return config

def obtener_lista_canales(config):

    # Obtener la lista de canales desde TVHeadend con autenticación digest
    url = f"http://{config['TVHEADEND_IP']}/api/channel/grid"
    filter = {
        "field": "number",
        "value": 0
    }

    # Configurar los parámetros de la solicitud
    parametros = {
        "limit": 100,  # Limitar a 500 canales para fines de depuración
        "meta": 0
    }

    try:
        response = requests.get(url, auth=HTTPDigestAuth(config['TVHEADEND_USERNAME'], config['TVHEADEND_PASSWORD']), params=parametros)
        response.raise_for_status()  # Verificar si hay errores en la respuesta
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud de la API: {e}")
        return []

    if debug:
        # Imprimir mensajes de depuración
        print(f"Debug - URL de la solicitud: {response.url}")
        print(f"Debug - Respuesta de la solicitud: {response.text}")

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"Error al decodificar la respuesta JSON: {e}")
        return []

    # Obtener canales activos sin filtrar
    canales_activos = [(channel['number'], channel['name']) for channel in data.get('entries', [])]
    
    if debug:
        # Imprimir información detallada sobre los canales
        print("Debug - Información detallada de los canales:")
        for channel in data.get('entries', []):
             number = channel.get('number', 'N/A')
             name = channel.get('name', 'N/A')
             enabled = channel.get('enabled', 'N/A')
             print(f"Debug - Canal: {number} - {name} (Habilitado: {enabled})")

    # Ordenar por el número del canal
    canales_activos.sort(key=lambda x: x[0])

    return canales_activos

import subprocess

def reproducir_canal(nombre_canal, config):
    # Obtener el número del canal a partir del nombre
    canales = obtener_lista_canales(config)
    for canal in canales:
        if canal[1] == nombre_canal:
            numero_canal = canal[0]
            break

    # Construir la URL del flujo del canal usando el número del canal y las credenciales
    url = f"http://{config['TVHEADEND_USERNAME']}:{config['TVHEADEND_PASSWORD']}@{config['TVHEADEND_IP']}/stream/channelnumber/{numero_canal}?profile=pass"

    # Construir el comando para reproducir el canal en omxplayer
    comando = ["/usr/bin/omxplayer", f"{url}"]

    # Imprimir mensajes de depuración
    if debug:
        print(f"Debug - Comando para reproducir el canal: {' '.join(comando)}")

    # Redirigir la salida estándar y estándar de error a /dev/null (o puedes redirigir a un archivo si prefieres)
    with open(os.devnull, 'w') as devnull:
        # Ejecutar el comando en un proceso separado
        subprocess.Popen(comando, stdout=devnull, stderr=devnull)

def obtener_tecla():
    termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    return sys.stdin.read(1)

def main():
    while True:

	# Obtener o solicitar la configuración de TVHeadend
        configuracion_tvheadend = obtener_configuracion_tvheadend()

        # Obtener la lista de canales activos sin ordenar
        canales = obtener_lista_canales(configuracion_tvheadend)

        # Ordenar la lista de canales por el número del canal
        canales.sort(key=lambda x: x[0])

    	# Imprimir la lista de canales
        print("Canales disponibles:")
        for i, (numero, canal) in enumerate(canales, start=1):
             print(f"{i}. {numero}: {canal}")

    	# Solicitar al usuario que elija un canal sin pulsar "Enter"
        print("Seleccione el número del canal que desea ver (0 para salir): ", end='', flush=True)

        seleccion = ''
        while seleccion == '':
            seleccion = obtener_tecla()

        # Verificar si el usuario quiere salir
        if seleccion == '0':
            print("\nSaliendo del programa.")
            break

        try:
            seleccion = int(seleccion) - 1

            # Verificar si la selección es válida
            if 0 <= seleccion < len(canales):
                canal_seleccionado = canales[seleccion][1]
                print(f"Reproduciendo el canal: {canal_seleccionado}")

                # Matar todos los procesos omxplayer
                os.system("pkill -9 omxplayer")

                # Reproducir el canal seleccionado
                reproducir_canal(canal_seleccionado, configuracion_tvheadend)
            else:
                print("Selección inválida.")
        except ValueError:
            print("Entrada no válida.")

        # Matar todos los procesos omxplayer
        subprocess.run(["pkill", "-9", "omxplayer"], check=True)

        # Reproducir el canal seleccionado
        reproducir_canal(canal_seleccionado, configuracion_tvheadend)
        
if __name__ == "__main__":
   main()

