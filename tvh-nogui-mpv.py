#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import requests
from requests.auth import HTTPDigestAuth
import subprocess
import json
import sys
import termios

# --- CONFIGURACIÓN ---
debug = False
CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), "tvheadend_config.json")

def obtener_configuracion_tvheadend():
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as file:
            return json.load(file)
    else:
        config = {
            "TVHEADEND_IP": input("IP y Puerto (ej: 192.168.1.50:9981): "),
            "TVHEADEND_USERNAME": input("Usuario: "),
            "TVHEADEND_PASSWORD": input("Contraseña: "),
        }
        with open(CONFIG_FILE_PATH, "w") as file:
            json.dump(config, file, indent=2)
        return config

def obtener_lista_canales(config):
    url = f"http://{config['TVHEADEND_IP']}/api/channel/grid"
    parametros = {"limit": 500, "meta": 0}
    
    try:
        response = requests.get(
            url, 
            auth=HTTPDigestAuth(config['TVHEADEND_USERNAME'], config['TVHEADEND_PASSWORD']), 
            params=parametros,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Extraemos número y nombre, asegurando que el número sea entero para ordenar
        canales = []
        for c in data.get('entries', []):
            canales.append({
                "numero": int(c.get('number', 0)),
                "nombre": c.get('name', 'S/N')
            })
        
        # Ordenar por número de canal
        canales.sort(key=lambda x: x['numero'])
        return canales
    except Exception as e:
        print(f"\n[!] Error conectando a TVHeadend: {e}")
        return []

def reproducir_canal(numero_canal, config):
    # Matar procesos previos
    subprocess.run(["pkill", "-9", "mpv"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    
    host = config['TVHEADEND_IP']
    user = config['TVHEADEND_USERNAME']
    pw = config['TVHEADEND_PASSWORD']
    
    # URL Limpia (sin usuario:pass@)
    url = f"http://{host}/stream/channelnumber/{numero_canal}"
    
    # Pasamos el usuario y pass de forma segura a través de los flags de MPV
    comando = [
        "mpv", 
        "--ontop", 
        "--no-border", 
        f"--http-header-fields=Authorization: Basic " + 
        # Esto envía las credenciales de forma estándar
        subprocess.check_output(f"echo -n {user}:{pw} | base64", shell=True).decode().strip(),
        url
    ]
    
    # Si lo anterior te parece muy complejo, prueba primero con esta versión más simple:
    # comando = ["mpv", "--ontop", "--no-border", f"--user={user}", f"--password={pw}", url]

    print(f">> Intentando conectar a: {url}")
    
    try:
        subprocess.Popen(comando)
    except Exception as e:
        print(f"Error al lanzar MPV: {e}")
        
def main():
    # Guardar estado de la terminal para restaurarla al final
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        config = obtener_configuracion_tvheadend()
        canales = obtener_lista_canales(config)
        
        if not canales:
            print("No se encontraron canales. Revisa la configuración.")
            return

        while True:
            os.system('clear')
            print("=== TVHEADEND NOGUI PLAYER ===")
            print(f"Canales cargados: {len(canales)}\n")
            
            # Mostrar lista (puedes ajustar el rango si tienes cientos)
            for c in canales[:40]: # Mostramos los primeros 40
                print(f"{c['numero']:>3}: {c['nombre']}")
            
            print("\n[ 0: Salir | Escribe el número del canal y pulsa Enter ]")
            
            try:
                seleccion = input("\nSelección: ")
                
                if seleccion == '0':
                    print("Saliendo...")
                    subprocess.run(["pkill", "-9", "mpv"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                    break
                
                num_seleccionado = int(seleccion)
                
                # Buscar si el número existe en nuestra lista
                canal_valido = next((c for c in canales if c['numero'] == num_seleccionado), None)
                
                if canal_valido:
                    print(f">> Sintonizando: {canal_valido['nombre']}...")
                    reproducir_canal(num_seleccionado, config)
                else:
                    print("Ese número de canal no existe.")
                    
            except ValueError:
                print("Por favor, introduce un número válido.")
            
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
    finally:
        # Restaurar la terminal SIEMPRE
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("Terminal restaurada correctamente.")

if __name__ == "__main__":
    main()
