"""Constantes de la integración kodi_link."""
from datetime import timedelta

DOMAIN = "kodi_link"
ADDON_ID = "service.ha_link"  # remitente de lo que llega del addon
EMISOR = DOMAIN  # remitente de lo que la integración manda al addon
SUBENTRY_KODI = "kodi"

# Entrada principal
CONF_ETIQUETA_VE = "etiqueta_ve"
CONF_ETIQUETA_ACTUA = "etiqueta_actua"
NOMBRE_ETIQUETA_VE = "Kodi: ve"
NOMBRE_ETIQUETA_ACTUA = "Kodi: actúa"

# Subentrada de cada Kodi
CONF_KODI = "kodi"
CONF_NIVEL = "nivel"
NIVEL_NADA = "nada"
NIVEL_VE = "ve"
NIVEL_ACTUA = "actua"
NIVELES = [NIVEL_NADA, NIVEL_VE, NIVEL_ACTUA]
CONF_VISTA = "vista"  # lo que se abre desde Programas: tablero (A), filas (C) o el listado (K1)
VISTAS = ["tablero", "filas", "listado"]
VISTA_DEFECTO = "tablero"
CONF_TECLA = "tecla"  # tecla del mando que abre el panel lateral (B) durante la reproducción
TECLAS = ["ninguna", "roja", "verde", "amarilla", "azul"]
TECLA_DEFECTO = "azul"
# Avisos (fase 3): qué hace este Kodi con cada gravedad
GRAVEDADES = ["aviso", "importante", "grave"]
COMPORTAMIENTOS = ["nada", "tarjeta", "pausar"]  # nada: no se enseña; tarjeta: sale y se va sola; pausar: se queda
CONF_CON = {g: f"con_{g}" for g in GRAVEDADES}
COMPORTAMIENTO_DEFECTO = {"aviso": "tarjeta", "importante": "tarjeta", "grave": "pausar"}
TIPOS_AVISO = ["info", "timbre", "puerta", "ventana", "garaje", "movimiento", "alarma", "humo", "agua", "lluvia",
               "calefaccion", "luz", "sistema"]
DURACION_AVISO = 10  # s

# Estado del enlace con cada Kodi
DESACTIVADO = "desactivado"
DESCONECTADO = "desconectado"
SIN_ADDON = "sin_addon"
CONECTADO = "conectado"

ESTADOS_ENLACE = [DESACTIVADO, DESCONECTADO, SIN_ADDON, CONECTADO]

SENAL = f"{DOMAIN}_actualizado"

LATIDO = timedelta(seconds=60)
AGRUPAR_CAMBIOS = 0.3  # s: los cambios de estado seguidos salen en un solo mensaje
AGRUPAR_REGISTRO = 1.0  # s: igual con los cambios de etiquetas, áreas y nombres
ESPERA_MIN = 5  # s entre intentos de conexión, que se dobla hasta ESPERA_MAX
ESPERA_MAX = 60
