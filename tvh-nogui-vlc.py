#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import select
import subprocess
import sys
import termios
import time
import tty
import requests
from requests.auth import HTTPDigestAuth

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
    """Obtiene la lista completa de canales y la información EPG actual."""
    base_url = f"http://{config['TVHEADEND_IP']}/api"
    auth = HTTPDigestAuth(config["TVHEADEND_USERNAME"], config["TVHEADEND_PASSWORD"])

    try:
        # 1. Obtener Canales
        resp_canales = requests.get(
            f"{base_url}/channel/grid", auth=auth, params={"limit": 1000}, timeout=5
        )
        data_canales = resp_canales.json()

        # 2. Obtener EPG actual
        resp_epg = requests.get(
            f"{base_url}/epg/events/grid",
            auth=auth,
            params={"limit": 1000, "mode": "now"},
            timeout=5,
        )
        data_epg = resp_epg.json()

        guia = {
            event.get("channelUuid"): event.get("title", "")
            for event in data_epg.get("entries", [])
        }

        canales = []
        for c in data_canales.get("entries", []):
            uuid = c.get("uuid")
            canales.append(
                {
                    "num": c.get("number"),
                    "nom": c.get("name", "Sin nombre"),
                    "ahora": guia.get(uuid, "Sin información"),
                }
            )

        canales.sort(key=lambda x: x["num"] if x["num"] is not None else 9999)
        return canales
    except Exception as e:
        print(f"\nError cargando datos de TVHeadend: {e}")
        return []


def reproducir_canal(numero_canal, config):
    # Cierre de instancias previas de VLC
    subprocess.run("pkill -9 vlc > /dev/null 2>&1", shell=True)

    user = config["TVHEADEND_USERNAME"]
    pw = config["TVHEADEND_PASSWORD"]
    host = config["TVHEADEND_IP"]

    url = f"http://{user}:{pw}@{host}/stream/channelnumber/{numero_canal}"

    # Opciones de VLC equivalentes a las de MPV:
    # --video-on-top: Siempre encima
    # --no-video-title-show: Oculta el título superpuesto en pantalla
    # --zoom=0.5: Escala la ventana al 50%
    # --qt-minimal-view: Interfaz compacta/mínima de VLC
    comando = [
        "vlc",
        "--video-on-top",
        "--no-video-title-show",
        "--zoom=0.5",
        "--qt-minimal-view",
        url,
    ]

    subprocess.Popen(
        comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def leer_tecla_con_timeout(timeout=1.0):
    """Lee un carácter individual de la terminal."""
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


def obtener_seleccion():
    acumulado = ""
    print("\nOpción / Nº de canal: ", end="", flush=True)
    while True:
        tecla = leer_tecla_con_timeout(None if not acumulado else 1.0)
        if tecla is None:
            break

        # Siguiente (+) o Anterior (-)
        if tecla in ["+", "-"]:
            return tecla

        # Recargar (r) o Salir (q)
        if tecla.lower() in ["r", "q"]:
            return tecla.lower()

        # Salir con 0 (si es el primer número pulsado)
        if tecla == "0" and not acumulado:
            return "0"

        # Acumular números de canal (ej: 12, 105)
        if tecla.isdigit():
            acumulado += tecla
            print(tecla, end="", flush=True)
        else:
            break
    return acumulado


def main():
    config = obtener_configuracion_tvheadend()
    canales = []
    pagina_actual = 0
    POR_PAGINA = 15

    while True:
        if not canales:
            canales = obtener_canales_con_epg(config)
            if not canales:
                print("No se encontraron canales. Reintentando en 5 segundos...")
                time.sleep(5)
                continue

        total_paginas = max(1, (len(canales) + POR_PAGINA - 1) // POR_PAGINA)
        inicio = pagina_actual * POR_PAGINA
        fin = inicio + POR_PAGINA
        canales_pagina = canales[inicio:fin]

        os.system("clear" if os.name == "posix" else "cls")
        print("=" * 70)
        print(
            f" TVHEADEND CLIENT (VLC) - Pág {pagina_actual + 1}/{total_paginas} (Total: {len(canales)} canales)"
        )
        print("=" * 70)
        print(f"{'CANAL Nº':>8} | {'NOMBRE':<20} | {'AHORA EN ANTENA'}")
        print("-" * 70)

        for c in canales_pagina:
            num_str = str(c["num"]) if c["num"] is not None else "---"
            nombre = c["nom"][:20]
            evento = c["ahora"][:36]
            print(f"{num_str:>8} | {nombre:<20} | {evento}")

        print("-" * 70)
        print("[Nº Canal]: Sintonizar | [+]: Sig. Pág | [-]: Pág. Ant")
        print("[R]: Recargar EPG      | [0]: Salir")

        sel = obtener_seleccion()

        if sel in ["0", "q"]:
            print("\nSaliendo del programa...")
            subprocess.run("pkill -9 vlc > /dev/null 2>&1", shell=True)
            break
        elif sel == "+":
            if pagina_actual < total_paginas - 1:
                pagina_actual += 1
        elif sel == "-":
            if pagina_actual > 0:
                pagina_actual -= 1
        elif sel == "r":
            canales = []
            pagina_actual = 0
        elif sel.isdigit():
            num_elegido = int(sel)
            canal_encontrado = next(
                (c for c in canales if c["num"] == num_elegido), None
            )
            if canal_encontrado:
                print(
                    f"\n>> Sintonizando {canal_encontrado['nom']} (Canal {canal_encontrado['num']})..."
                )
                reproducir_canal(canal_encontrado["num"], config)
                time.sleep(1)
            else:
                print(f"\n>> El número de canal {num_elegido} no existe en la lista.")
                time.sleep(1.5)


if __name__ == "__main__":
    main()
