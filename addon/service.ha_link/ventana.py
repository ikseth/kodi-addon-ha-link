"""Ventana propia de HA Link (K2): tablero por áreas (A), filas por estancia (C) y panel lateral (B).

Se abre con RunScript(<esta ruta>, tablero|filas|lateral[, área]); el tablero empieza en ese área si se da. Capa fina: el modelo está en
resources/lib/ha_link/tablero.py (sin xbmc, con pruebas) y las ventanas XML las genera
herramientas/generar_ventanas.py. Lee la vista que deja el servicio en la ventana Home y la refresca en vivo.
"""
import json
import os
import sys
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon("service.ha_link")
RAIZ = ADDON.getAddonInfo("path")
sys.path.insert(0, os.path.join(RAIZ, "resources", "lib"))

from ha_link import avisos as A  # noqa: E402
from ha_link import listado  # noqa: E402
from ha_link import tablero as T  # noqa: E402

PROPIEDAD = "ha_link.vista"
ABIERTO = "ha_link.lateral_abierto"
AVISO = "ha_link.aviso"
AVISO_ABIERTO = "ha_link.aviso_abierto"
CERRAR_FIJA = (xbmcgui.ACTION_SELECT_ITEM, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU)
MEDIA = os.path.join(RAIZ, "resources", "skins", "Default", "media", "k2")
ICONOS = os.path.join(RAIZ, "resources", "media", "iconos")
IMAGENES = ("glifo", "bloque", "halo", "lavado", "aro", "ind1", "ind1_glifo", "ind2", "ind2_glifo", "ind3",
            "ind3_glifo")
CADA = 0.15  # s entre dos miradas a la vista y a la selección

AREAS, BALDOSAS = 100, 200
PRIMERA_FILA = 301
AHORA_1, AHORA_3, AQUI = 400, 402, 401
ATRAS = (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU)


def textos():
    return {clave: ADDON.getLocalizedString(ident) for clave, ident in T.IDS.items()}


def leer_vista():
    texto = xbmcgui.Window(10000).getProperty(PROPIEDAD)
    try:
        return texto, json.loads(texto or "null")
    except ValueError:
        return texto, None


def ruta(nombre):
    return os.path.join(MEDIA, nombre) if nombre else ""


def props_completas(props):
    return {k: (ruta(v) if k in IMAGENES else v) for k, v in props.items()}


def item(baldosa):
    li = xbmcgui.ListItem(label=baldosa.linea1, label2=baldosa.linea2, offscreen=True)
    li.setProperties(props_completas(baldosa.props))
    li.setProperty("entidad", baldosa.entidad or "")
    return li


def rellenar(control, baldosas):
    """Rellena una lista. Si son las mismas entidades en el mismo orden, actualiza en su sitio (sin parpadeo
    ni perder el foco); si no, la rehace y deja la selección donde estaba."""
    ids = [b.entidad for b in baldosas]
    if control.size() == len(ids) and all(control.getListItem(i).getProperty("entidad") == ids[i]
                                          for i in range(len(ids))):
        for i, b in enumerate(baldosas):
            li = control.getListItem(i)
            li.setLabel(b.linea1)
            li.setLabel2(b.linea2)
            li.setProperties(props_completas(b.props))
        return
    pos = control.getSelectedPosition()
    control.reset()
    control.addItems([item(b) for b in baldosas])
    if baldosas:
        control.selectItem(min(max(pos, 0), len(baldosas) - 1))


class Base(object):
    """Lo común (mixin): textos fijos, cabecera, refresco en vivo y la pulsación en una entidad (solo lectura).

    El refresco va en un hilo: onInit tiene que volver enseguida para que Kodi atienda el mando.
    """

    def onInit(self):
        self.t = textos()
        self.texto_vista = None
        self.vista = None
        self.entidades = {}
        self.seguir = True
        self.cerrojo = threading.Lock()
        for clave in ("ver", "salir", "volver", "escena"):
            self.setProperty("txt_" + clave, T.texto(self.t, clave))
        self.setProperty("casa", T.texto(self.t, "casa"))
        self.setProperty("txt_ahora", T.texto(self.t, "ahora").upper())
        with self.cerrojo:
            self.actualizar(forzar=True)
            self.enfocar()
        self.hilo = threading.Thread(target=self._bucle)
        self.hilo.daemon = True
        self.hilo.start()

    def _bucle(self):
        monitor = xbmc.Monitor()
        while self.seguir and not monitor.abortRequested():
            if monitor.waitForAbort(CADA) or not self.seguir:
                break
            try:
                with self.cerrojo:
                    self.vigilar()
            except RuntimeError:  # la ventana se está cerrando
                break

    def vigilar(self):
        self.actualizar()

    def actualizar(self, forzar=False):
        texto, vista = leer_vista()
        if not forzar and texto == self.texto_vista:
            return
        self.texto_vista, self.vista = texto, vista
        self.entidades = {e.get("id"): e for e in (vista or {}).get("e") or []}
        for k, v in T.cabecera(vista, self.t).items():
            self.setProperty(k, ruta(v) if k == "estado_glifo" else v)
        self.setProperty("aviso", T.aviso(vista, self.t))
        self.pintar()

    def pintar(self):
        raise NotImplementedError

    def enfocar(self):
        """Foco inicial, ya con las listas llenas (el defaultcontrol del XML llega antes y no puede)."""

    def onClick(self, control_id):
        try:
            li = self.getControl(control_id).getSelectedItem()
        except (RuntimeError, TypeError):
            return
        e = self.entidades.get(li.getProperty("entidad")) if li else None
        if not e:
            return
        icono = os.path.join(ICONOS, listado.icono(e.get("d"), e.get("c"), e.get("t")))
        detalle = " · ".join(x for x in (e.get("v"), T.texto(self.t, "solo_lectura")) if x)
        xbmcgui.Dialog().notification(e.get("n") or e.get("id"), detalle, icono, 2500, False)

    def onAction(self, action):
        if action.getId() in ATRAS:
            self.cerrar()

    def cerrar(self):
        self.seguir = False
        self.close()


class Tablero(Base, xbmcgui.WindowXML):
    """A: áreas a la izquierda y baldosas del área elegida a la derecha."""

    area_inicial = None

    def onInit(self):
        self.areas = []
        self.sel = -1
        Base.onInit(self)

    def enfocar(self):
        self.setFocusId(AREAS)

    def vigilar(self):
        Base.vigilar(self)
        pos = self.getControl(AREAS).getSelectedPosition()
        if pos != self.sel:
            self.sel = pos
            self.pintar_area()

    def pintar(self):
        lista = self.getControl(AREAS)
        anteriores = [a.id for a in self.areas]
        elegida = anteriores[self.sel] if 0 <= self.sel < len(anteriores) else None
        if not anteriores and self.area_inicial:
            elegida, self.area_inicial = self.area_inicial, None
        self.areas = T.areas(self.vista, self.t)
        ids = [a.id for a in self.areas]
        if ids == anteriores and lista.size() == len(ids):
            for i, a in enumerate(self.areas):
                lista.getListItem(i).setProperties(props_completas(a.props))
        else:
            lista.reset()
            for a in self.areas:
                li = xbmcgui.ListItem(label=a.nombre, offscreen=True)
                li.setProperties(props_completas(a.props))
                lista.addItem(li)
            if self.areas:
                lista.selectItem(ids.index(elegida) if elegida in ids else 0)
        self.sel = lista.getSelectedPosition()
        self.pintar_area()

    def pintar_area(self):
        a = self.areas[self.sel] if 0 <= self.sel < len(self.areas) else None
        self.setProperty("area", a.nombre if a else "")
        rellenar(self.getControl(BALDOSAS), a.baldosas if a else [])


class Filas(Base, xbmcgui.WindowXML):
    """C: una fila por área («Ahora mismo» primero) con sus baldosas en horizontal."""

    def enfocar(self):
        self.setFocusId(PRIMERA_FILA)

    def pintar(self):
        areas = T.areas(self.vista, self.t)[:T.MAX_FILAS]
        for i in range(T.MAX_FILAS):
            pre = "fila%d_" % i
            a = areas[i] if i < len(areas) else None
            self.setProperty(pre + "nombre", a.nombre if a else "")
            for k, v in (props_completas(a.props) if a else {}).items():
                self.setProperty(pre + k, v)
            if not a:
                for k in ("ind1", "ind2", "ind3", "temp", "tranquilo"):
                    self.setProperty(pre + k, "")
            rellenar(self.getControl(PRIMERA_FILA + i), a.baldosas if a else [])


class Lateral(Base, xbmcgui.WindowXMLDialog):
    """B: panel sobre el vídeo. Pausa al abrir y reanuda al cerrar si fue él quien pausó."""

    def onInit(self):
        self.pausado_aqui = False
        jugador = xbmc.Player()
        if jugador.isPlayingVideo() and not xbmc.getCondVisibility("Player.Paused"):
            jugador.pause()
            self.pausado_aqui = True
        Base.onInit(self)

    def pintar(self):
        _, ahora, titulo_aqui, aqui = T.lateral(self.vista, self.t)
        self.setProperty("aqui", titulo_aqui.upper())
        hay_datos = bool(self.vista and self.vista.get("e"))
        self.setProperty("tranquilo", T.texto(self.t, "tranquilo") if hay_datos and not ahora else "")
        rellenar(self.getControl(AHORA_1), ahora if titulo_aqui else [])
        rellenar(self.getControl(AHORA_3), [] if titulo_aqui else ahora)
        rellenar(self.getControl(AQUI), aqui)
        if self.getFocusId() not in (AHORA_1, AHORA_3, AQUI):
            self.setFocusId((AHORA_1 if ahora else AQUI) if titulo_aqui else AHORA_3)

    def cerrar(self):
        if self.pausado_aqui and xbmc.getCondVisibility("Player.Paused"):
            xbmc.Player().pause()
        Base.cerrar(self)


class Aviso(xbmcgui.WindowXMLDialog):
    """Tarjeta de un aviso sobre lo que haya en pantalla. «tarjeta»: se va sola. «pausar»: pausa el vídeo y se queda
    hasta que se cierra con OK o Atrás. Si llega otro aviso con ella abierta, se cambia por el nuevo."""

    def onInit(self):
        self.t = textos()
        self.texto = None
        self.hasta = None
        self.fija = False
        self.seguir = True
        self.cerrojo = threading.Lock()
        with self.cerrojo:
            self.mirar()
        self.hilo = threading.Thread(target=self._bucle)
        self.hilo.daemon = True
        self.hilo.start()

    def mirar(self):
        texto = xbmcgui.Window(10000).getProperty(AVISO)
        if texto == self.texto:
            return
        self.texto = texto
        try:
            aviso = A.normalizar(json.loads(texto or "null"))
        except ValueError:
            aviso = None
        if not aviso:
            self.cerrar()
            return
        for k, v in A.tarjeta(aviso, self.t).items():
            self.setProperty(k, ruta(v) if k in ("glifo", "bloque", "halo") else v)
        self.fija = aviso["acc"] == "pausar"
        self.hasta = None if self.fija else time.time() + aviso["d"]
        if self.fija and xbmc.Player().isPlayingVideo() and not xbmc.getCondVisibility("Player.Paused"):
            xbmc.Player().pause()

    def _bucle(self):
        monitor = xbmc.Monitor()
        while self.seguir and not monitor.abortRequested():
            if monitor.waitForAbort(0.25) or not self.seguir:
                break
            try:
                with self.cerrojo:
                    self.mirar()
                    if self.hasta and time.time() > self.hasta:
                        self.cerrar()
            except RuntimeError:
                break

    def onAction(self, action):
        if not self.fija or action.getId() in CERRAR_FIJA:
            self.cerrar()

    def cerrar(self):
        self.seguir = False
        self.close()


def abrir(que, area=None):
    if que == "aviso":
        casa = xbmcgui.Window(10000)
        if casa.getProperty(AVISO_ABIERTO):
            return
        casa.setProperty(AVISO_ABIERTO, "1")
        try:
            Aviso("ha_link_aviso.xml", RAIZ, "Default", "1080i").doModal()
        finally:
            casa.clearProperty(AVISO_ABIERTO)
        return
    if que == "lateral":
        casa = xbmcgui.Window(10000)
        if casa.getProperty(ABIERTO):
            return
        casa.setProperty(ABIERTO, "1")
        try:
            Lateral("ha_link_lateral.xml", RAIZ, "Default", "1080i").doModal()
        finally:
            casa.clearProperty(ABIERTO)
        return
    clase, xml = (Filas, "ha_link_filas.xml") if que == "filas" else (Tablero, "ha_link_tablero.xml")
    ventana = clase(xml, RAIZ, "Default", "1080i")
    if area:
        ventana.area_inicial = area
    ventana.doModal()
    del ventana


if __name__ == "__main__":
    try:
        abrir(sys.argv[1] if len(sys.argv) > 1 else "tablero", sys.argv[2] if len(sys.argv) > 2 else None)
    except Exception as err:  # noqa: BLE001 - que un fallo de la ventana quede en el log
        xbmc.log("[service.ha_link] error en la ventana: %s" % err, xbmc.LOGERROR)
        raise
