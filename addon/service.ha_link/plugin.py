"""Entrada de HA Link desde Programas: abre la ventana propia (K2) o el listado (K1).

Qué se abre lo decide la configuración de este Kodi en HA (pantalla: tablero, filas o listado). El listado es una
capa fina: lee la vista que deja el servicio en la ventana Home y pinta las filas que calcula
resources/lib/ha_link/listado.py (sin xbmc, con tests). «?modo=listado» lo abre siempre, y
«?abrir=tablero|filas|lateral» abre esa ventana (por ejemplo desde HA con Addons.ExecuteAddon).
"""
import json
import os
import sys
import time
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

ADDON = xbmcaddon.Addon()
RAIZ = ADDON.getAddonInfo("path")
sys.path.insert(0, os.path.join(RAIZ, "resources", "lib"))

from ha_link import listado  # noqa: E402

PROPIEDAD = "ha_link.vista"
ICONOS = os.path.join(RAIZ, "resources", "media", "iconos")
BASE = sys.argv[0]
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else -1
PARAMS = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}


def textos():
    return {clave: ADDON.getLocalizedString(ident) for clave, ident in listado.IDS.items()}


def vista():
    try:
        return json.loads(xbmcgui.Window(10000).getProperty(PROPIEDAD) or "null")
    except ValueError:
        return None


def ruta_icono(nombre):
    ruta = os.path.join(ICONOS, nombre)
    if os.path.exists(ruta):
        return ruta
    return os.path.join(ICONOS, "generico_%s" % nombre.rsplit("_", 1)[-1])


def pintar(filas):
    for f in filas:
        li = xbmcgui.ListItem(label=f.etiqueta, label2=f.etiqueta2, offscreen=True)
        if f.icono:
            icono = ruta_icono(f.icono)
            li.setArt({"icon": icono, "thumb": icono})
        url = "%s?%s" % (BASE, urlencode(f.destino)) if f.destino else "%s?nada=1" % BASE
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=f.carpeta)
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=False)


def main():
    v = vista()
    t = textos()
    if "ver" in PARAMS:  # pulsación en una entidad: en esta fase solo se informa
        info = listado.detalle(v, PARAMS["ver"], t)
        if info:
            xbmcgui.Dialog().notification(info[0], info[1], ruta_icono(info[2]), 3000, False)
        return
    if "nada" in PARAMS:
        return
    if PARAMS.get("abrir") in ("tablero", "filas", "lateral"):
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        xbmc.executebuiltin("RunScript(%s,%s)" % (os.path.join(RAIZ, "ventana.py"), PARAMS["abrir"]))
        return
    if "area" in PARAMS:
        pintar(listado.area(v, PARAMS["area"], time.time(), t))
        return
    pantalla = ((v or {}).get("cfg") or {}).get("vista") or "tablero"
    if PARAMS.get("modo") != "listado" and pantalla in ("tablero", "filas"):
        # La raíz abre la ventana propia y no se queda en un listado vacío
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        xbmc.executebuiltin("RunScript(%s,%s)" % (os.path.join(RAIZ, "ventana.py"), pantalla))
        return
    pintar(listado.raiz(v, time.time(), t))


if __name__ == "__main__":
    try:
        main()
    except Exception as err:  # noqa: BLE001 - que el listado no deje a Kodi esperando
        xbmc.log("[service.ha_link] error en el listado: %s" % err, xbmc.LOGERROR)
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
