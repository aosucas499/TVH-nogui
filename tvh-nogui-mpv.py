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
debug = False
CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), "tvheadend_config.json")

def obtener_configuracion_tvheadend():
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as file:
            return json.load(file)
    else:
        config = {
            "TVHEADEND_IP": input("Ingrese IP:Puerto: "),
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
            params={"limit": 200},
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
    subprocess.Popen(["mpv", "--ontop", "--no-border", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def leer_tecla_con_timeout(timeout=1.2):
    """Espera una tecla durante un tiempo determinado."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        # Esperar a que haya algo que leer en el buffer de entrada
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            return sys.stdin.read(1)
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def obtener_seleccion_inteligente():
    """Permite escribir varios números y sintoniza tras una pausa."""
    acumulado = ""
    print("\nEscribe el número del canal: ", end='', flush=True)
    
    while True:
        # La primera tecla espera infinito, las siguientes esperan 1.2 segundos
        timeout = None if not acumulado else 1.2
        tecla = leer_tecla_con_timeout(timeout)
        
        if tecla is None: # Se acabó el tiempo
            break
        
        if tecla == '0' and not acumulado:
            return "0"
        
        if tecla.isdigit():
            acumulado += tecla
            print(tecla, end='', flush=True)
        else:
            # Si pulsas algo que no es un número (como espacio), sintoniza ya
            break
            
    return acumulado

def main():
    config = obtener_configuracion_tvheadend()
    canales = obtener_lista_canales(config)
    
    while True:
        os.system('clear')
        print("=== TVH PLAYER (Modo Mando TV) ===")
        for i, (num, nombre) in enumerate(canales, start=1):
            if i <= 30: print(f"{i}. [{num}] {nombre}")
        
        print(f"\nPulsa números para sintonizar (0 para salir).")
        
        seleccion = obtener_seleccion_inteligente()
        
        if seleccion == "0":
            subprocess.run("pkill -9 mpv > /dev/null 2>&1", shell=True)
            break
            
        if seleccion:
            try:
                indice = int(seleccion) - 1
                if 0 <= indice < len(canales):
                    num_canal = canales[indice][0]
                    print(f"\n>> Sintonizando {canales[indice][1]}...")
                    reproducir_canal(num_canal, config)
                    time.sleep(1)
                else:
                    print("\n[!] Número no válido.")
                    time.sleep(1)
            except ValueError:
                pass

if __name__ == "__main__":
    main()
