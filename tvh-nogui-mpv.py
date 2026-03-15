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

def obtener_canales_con_epg(config):
    """Obtiene canales y lo que están emitiendo ahora mismo."""
    base_url = f"http://{config['TVHEADEND_IP']}/api"
    auth = HTTPDigestAuth(config['TVHEADEND_USERNAME'], config['TVHEADEND_PASSWORD'])
    
    try:
        # 1. Obtener Canales
        resp_canales = requests.get(f"{base_url}/channel/grid", auth=auth, params={"limit": 300}, timeout=5)
        data_canales = resp_canales.json()
        
        # 2. Obtener EPG actual (lo que se echa ahora)
        resp_epg = requests.get(f"{base_url}/epg/events/grid", auth=auth, params={"limit": 300, "mode": "now"}, timeout=5)
        data_epg = resp_epg.json()
        
        # Mapear EPG por ID de canal
        guia = {event.get('channelUuid'): event.get('title', '') for event in data_epg.get('entries', [])}
        
        canales = []
        for c in data_canales.get('entries', []):
            uuid = c.get('uuid')
            canales.append({
                "num": c.get('number'),
                "nom": c.get('name'),
                "ahora": guia.get(uuid, "Sin información")
            })
        
        canales.sort(key=lambda x: x['num'] if x['num'] is not None else 999)
        return canales
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return []

def reproducir_canal(numero_canal, config):
    subprocess.run("pkill -9 mpv > /dev/null 2>&1", shell=True)
    user, pw, host = config['TVHEADEND_USERNAME'], config['TVHEADEND_PASSWORD'], config['TVHEADEND_IP']
    url = f"http://{user}:{pw}@{host}/stream/channelnumber/{numero_canal}"
    
    # Ventana redimensionable y con dragging activado
    comando = [
        "mpv", "--ontop", "--no-border", 
        "--window-scale=0.5", "--window-dragging=yes",
        url
    ]
    subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def leer_tecla_con_timeout(timeout=1.0):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.read(1) if rlist else None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def obtener_seleccion():
    acumulado = ""
    print("\nSintonizar canal nº: ", end='', flush=True)
    while True:
        tecla = leer_tecla_con_timeout(None if not acumulado else 1.0)
        if tecla is None: break
        if tecla == '0' and not acumulado: return "0"
        if tecla.isdigit():
            acumulado += tecla
            print(tecla, end='', flush=True)
        else: break
    return acumulado

def main():
    config = obtener_configuracion_tvheadend()
    
    while True:
        canales = obtener_canales_con_epg(config)
        os.system('clear')
        print(f"{'ID':>3} | {'CANAL':<20} | {'AHORA EN ANTENA'}")
        print("-" * 70)
        
        for i, c in enumerate(canales[:40], start=1):
            nombre = c['nom'][:20]
            evento = c['ahora'][:40]
            print(f"{i:>3}. {nombre:<20} | {evento}")
            
        print("-" * 70)
        print("Escribe el nº de la lista (0 para salir, R para actualizar):")
        
        sel = obtener_seleccion()
        
        if sel == "0": break
        if sel:
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(canales):
                    print(f"\n>> Poniendo {canales[idx]['nom']}...")
                    reproducir_canal(canales[idx]['num'], config)
                    time.sleep(1)
            except: pass

if __name__ == "__main__":
    main()
