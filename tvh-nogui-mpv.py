#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import requests
from requests.auth import HTTPDigestAuth
import subprocess
import json
import sys
import termios
import tty
import select
import time

# --- CONFIGURACIÓN ---
CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), "tvheadend_config.json")

def obtener_configuracion_tvheadend():
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as file:
            return json.load(file)
    else:
        config = {
            "TVHEADEND_IP": input("Ingrese IP:Puerto (ej: 192.168.1.3:9981): "),
            "TVHEADEND_USERNAME": input("Usuario: "),
            "TVHEADEND_PASSWORD": input("Contraseña: "),
        }
        with open(CONFIG_FILE_PATH, "w") as file:
            json.dump(config, file, indent=2)
        return config

def obtener_lista_canales(config):
    url = f"http://{config['TVHEADEND_IP']}/api/channel/grid"
    try:
        response = requests.get(
            url, 
            auth=HTTPDigestAuth(config['TVHEADEND_USERNAME'], config['TVHEADEND_PASSWORD']), 
            params={"limit": 300}, # Aumentamos el límite de la API
            timeout=5
        )
        data = response.json()
        canales = [(c.get('number'), c.get('name')) for c in data.get('entries', [])]
        canales.sort(key=lambda x: x[0])
        return canales
    except:
        return []

def reproducir_canal(numero_canal, config):
    subprocess.run("pkill -9 mpv > /dev/null 2>&1", shell=True)
    user, pw, host = config['TVHEADEND_USERNAME'], config['TVHEADEND_PASSWORD'], config['TVHEADEND_IP']
    url = f"http://{user}:{pw}@{host}/stream/channelnumber/{numero_canal}"
    # Agregamos --geometry para que no tape toda la terminal si quieres
    subprocess.Popen(["mpv", "--ontop", "--no-border", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def leer_tecla_con_timeout(timeout=1.2):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            return sys.stdin.read(1)
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def obtener_seleccion_mando():
    acumulado = ""
    print("\nSintonizar canal nº: ", end='', flush=True)
    while True:
        timeout = None if not acumulado else 1.0 # 1 segundo de espera tras la primera tecla
        tecla = leer_tecla_con_timeout(timeout)
        if tecla is None: break
        if tecla == '0' and not acumulado: return "0"
        if tecla.isdigit():
            acumulado += tecla
            print(tecla, end='', flush=True)
        else: break
    return acumulado

def main():
    config = obtener_configuracion_tvheadend()
    canales = obtener_lista_canales(config)
    
    if not canales:
        print("Error: No se pudieron cargar canales de TVHeadend.")
        return

    while True:
        os.system('clear')
        print("=== TVH MANDO A DISTANCIA (MPV) ===")
        print("-" * 60)
        
        # LÓGICA DE COLUMNAS: Mostramos hasta 90 canales en 3 columnas
        max_canales_mostrar = min(len(canales), 90)
        filas = (max_canales_mostrar + 2) // 3 # Calculamos filas necesarias
        
        for f in range(filas):
            linea = ""
            for c in range(3): # 3 columnas
                idx = f + (c * filas)
                if idx < len(canales):
                    num_lista = idx + 1
                    num_tvh = canales[idx][0]
                    nombre = canales[idx][1][:15] # Cortamos nombre si es muy largo
                    linea += f"{num_lista:>2}. [{num_tvh:>2}] {nombre:<18} | "
            print(linea)

        print("-" * 60)
        print("Escribe el nº de la lista y espera un momento... (0 para salir)")
        
        seleccion = obtener_seleccion_mando()
        
        if seleccion == "0":
            subprocess.run("pkill -9 mpv > /dev/null 2>&1", shell=True)
            print("\nApagando...")
            break
            
        if seleccion:
            try:
                indice = int(seleccion) - 1
                if 0 <= indice < len(canales):
                    num_tvh = canales[indice][0]
                    print(f"\n>> OK: {canales[indice][1]}")
                    reproducir_canal(num_tvh, config)
                    time.sleep(1)
                else:
                    print("\n[!] Error: El número no está en la lista.")
                    time.sleep(1.5)
            except ValueError:
                pass

if __name__ == "__main__":
    main()
