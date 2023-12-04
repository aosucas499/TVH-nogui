import requests
import configparser
import os

def cargar_configuracion():
    config = configparser.ConfigParser()
    config.read('configuracion.conf')
    return config

def guardar_configuracion(usuario, contraseña, ip_servidor, puerto):
    config = configparser.ConfigParser()
    config['tvheadend'] = {
        'usuario': usuario,
        'contraseña': contraseña,
        'ip_servidor': ip_servidor,
        'puerto': puerto
    }
    with open('configuracion.conf', 'w') as configfile:
        config.write(configfile)

def obtener_credenciales():
    usuario = input("Ingrese el nombre de usuario: ")
    contraseña = input("Ingrese la contraseña: ")
    ip_servidor = input("Ingrese la dirección IP del servidor: ")
    puerto = input("Ingrese el puerto del servidor: ")
    return usuario, contraseña, ip_servidor, puerto

def descargar_lista_canales():
    try:
        # Cargar configuración desde el archivo
        try:
            config = cargar_configuracion()
            usuario = config.get('tvheadend', 'usuario')
            contraseña = config.get('tvheadend', 'contraseña')
            ip_servidor = config.get('tvheadend', 'ip_servidor')
            puerto = config.get('tvheadend', 'puerto')
        except (configparser.NoSectionError, configparser.NoOptionError):
            # Si no se encuentra la sección, solicitar al usuario y guardar en la configuración
            usuario, contraseña, ip_servidor, puerto = obtener_credenciales()
            guardar_configuracion(usuario, contraseña, ip_servidor, puerto)

        # Construir la URL con las variables proporcionadas por el usuario
        url = f"http://{usuario}:{contraseña}@{ip_servidor}:{puerto}/playlist/auth/channels"

        # Realizar la solicitud GET para descargar el archivo M3U
        respuesta = requests.get(url)

        # Verificar si la solicitud fue exitosa (código de estado 200)
        if respuesta.status_code == 200:
            # Guardar el contenido en un archivo local
            with open("lista_canales.m3u", "wb") as archivo:
                archivo.write(respuesta.content)
            print("Archivo M3U descargado con éxito.")
        else:
    	    # Mostrar el mensaje de error
            print(f"Error al descargar la lista de canales. Código de estado: {respuesta.status_code}")
            # Borrar el archivo de configuración
            if os.path.isfile("configuracion.conf"):
                os.remove("configuracion.conf")

    except requests.RequestException as e:
    	# Mostrar el mensaje de error
        print(f"Error de conexión: {e}")
        # Borrar el archivo de configuración
        if os.path.isfile("configuracion.conf"):
        	os.remove("configuracion.conf")

if __name__ == "__main__":
    descargar_lista_canales()
