"""Genera los strings.po del addon a partir de listado.TEXTOS y tablero.TEXTOS (es) y de INGLES (en).

Uso: python3 herramientas/generar_strings.py
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, "addon", "service.ha_link")
sys.path.insert(0, os.path.join(ADDON, "resources", "lib"))
from ha_link import listado  # noqa: E402
from ha_link import tablero  # noqa: E402

INGLES = {
    "esperando": "Waiting for data from Home Assistant…",
    "esperando_2": "This Kodi must be added to the Kodi Link integration",
    "caducado": "No connection with Home Assistant",
    "caducado_2": "Data from {}",
    "nada_expuesto": "Nothing is exposed to this Kodi",
    "nada_expuesto_2": "Choose it in Home Assistant with the Kodi Link labels",
    "ahora": "Right now",
    "sin_area": "No area",
    "alerta_1": "1 alert",
    "alerta_n": "{} alerts",
    "activo_1": "1 active",
    "activo_n": "{} active",
    "todo_en_calma": "All quiet",
    "elementos_1": "1 item",
    "elementos_n": "{} items",
    "solo_lectura": "Read only",
}
INGLES_K2 = {
    "casa": "Home",
    "al_dia": "Up to date",
    "caducado": "Data from {}",
    "esperando": "Waiting for Home Assistant",
    "nada": "Nothing is exposed to this Kodi",
    "ahora": "Right now",
    "sin_area": "No area",
    "tranquilo": "All at rest",
    "escena": "Scene",
    "ver": "View",
    "salir": "Exit",
    "volver": "Back to the film",
    "cambiar_area": "Change area",
    "solo_lectura": "Read only",
    "estancias": "Rooms",
}
assert set(INGLES) == set(listado.TEXTOS), set(INGLES) ^ set(listado.TEXTOS)
assert set(INGLES_K2) == set(tablero.TEXTOS), set(INGLES_K2) ^ set(tablero.TEXTOS)
TODOS = [(ident, INGLES[c], listado.TEXTOS[c]) for c, ident in listado.IDS.items()]
TODOS += [(ident, INGLES_K2[c], tablero.TEXTOS[c]) for c, ident in tablero.IDS.items()]
TODOS.sort()

CABECERA = '''# Kodi Media Center language file
# Addon Name: HA Link
# Addon id: service.ha_link
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Language: %s\\n"

'''


def escribir(idioma, carpeta, traducir):
    ruta = os.path.join(ADDON, "resources", "language", carpeta)
    os.makedirs(ruta, exist_ok=True)
    with open(os.path.join(ruta, "strings.po"), "w", encoding="utf-8") as f:
        f.write(CABECERA % idioma)
        for ident, ingles, espanol in TODOS:
            f.write('msgctxt "#%d"\nmsgid "%s"\nmsgstr "%s"\n\n' % (ident, ingles, traducir(espanol)))


escribir("en_GB", "resource.language.en_gb", lambda es: "")
escribir("es_ES", "resource.language.es_es", lambda es: es)
print("ok")
