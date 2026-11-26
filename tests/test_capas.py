"""Las capas finas (service.py y plugin.py) con módulos xbmc* falsos, y comprobaciones del paquete."""
import importlib.util
import json
import os
import re
import sys
import types

import pytest

from ha_link import listado as L
from ha_link import tablero as TB

ADDON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "addon", "service.ha_link")


class Registro:
    def __init__(self):
        self.props = {}
        self.rpc = []
        self.builtins = []
        self.items = []
        self.fin = []
        self.avisos = []
        self.ruta = ""
        self.log = []
        self.ficheros = {}  # sistema de ficheros falso de xbmcvfs


@pytest.fixture
def kodi(monkeypatch):
    reg = Registro()
    xbmc = types.ModuleType("xbmc")
    xbmc.LOGDEBUG, xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 0, 1, 2, 3
    xbmc.log = lambda t, n=1: reg.log.append(t)
    xbmc.executeJSONRPC = lambda texto: reg.rpc.append(json.loads(texto)) or '{"result":"OK"}'
    xbmc.executebuiltin = reg.builtins.append
    xbmc.getInfoLabel = lambda e: reg.ruta if e == "Container.FolderPath" else ""

    class Monitor:
        def __init__(self):
            pass

        def abortRequested(self):
            return False

        def waitForAbort(self, t=0):
            return True

    xbmc.Monitor = Monitor
    xbmcaddon = types.ModuleType("xbmcaddon")

    class Addon:
        def getAddonInfo(self, clave):
            return {"id": "service.ha_link", "version": "0.1.0", "path": ADDON}[clave]

        def getLocalizedString(self, ident):
            return ""

    xbmcaddon.Addon = Addon
    xbmcgui = types.ModuleType("xbmcgui")

    class Window:
        def __init__(self, ident):
            pass

        def setProperty(self, k, v):
            reg.props[k] = v

        def getProperty(self, k):
            return reg.props.get(k, "")

        def clearProperty(self, k):
            reg.props.pop(k, None)

    class ListItem:
        def __init__(self, label="", label2="", offscreen=False):
            self.label, self.label2, self.art, self.props = label, label2, {}, {}

        def setProperties(self, props):
            self.props.update(props)

        def setArt(self, art):
            self.art = art

    class Dialog:
        def notification(self, *a):
            reg.avisos.append(a)

    xbmcgui.Window, xbmcgui.ListItem, xbmcgui.Dialog = Window, ListItem, Dialog
    xbmcplugin = types.ModuleType("xbmcplugin")
    xbmcplugin.addDirectoryItem = lambda h, url, li, isFolder=False: reg.items.append((url, li, isFolder))
    xbmcplugin.setContent = lambda h, c: None
    xbmcplugin.endOfDirectory = lambda h, **kw: reg.fin.append(kw)
    xbmcvfs = types.ModuleType("xbmcvfs")
    xbmcvfs.translatePath = lambda r: r.replace("special://profile/", "/perfil/")
    xbmcvfs.exists = lambda r: r in reg.ficheros
    xbmcvfs.delete = lambda r: reg.ficheros.pop(r, None) is not None
    xbmcvfs.mkdirs = lambda r: True

    class File:
        def __init__(self, ruta, modo="r"):
            self.ruta, self.modo = ruta, modo

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return reg.ficheros[self.ruta]

        def write(self, texto):
            reg.ficheros[self.ruta] = texto

    xbmcvfs.File = File
    for nombre, mod in (("xbmc", xbmc), ("xbmcaddon", xbmcaddon), ("xbmcgui", xbmcgui), ("xbmcplugin", xbmcplugin),
                        ("xbmcvfs", xbmcvfs)):
        monkeypatch.setitem(sys.modules, nombre, mod)
    return reg


def cargar(nombre, argv=None, monkeypatch=None):
    if argv is not None:
        monkeypatch.setattr(sys, "argv", argv)
    spec = importlib.util.spec_from_file_location("ha_link_" + nombre, os.path.join(ADDON, nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FOTO = {"p": 1, "s": "s1", "n": 1, "t": 1, "nivel": "ve", "areas": [{"id": "salon", "n": "Salón"}],
        "e": [{"id": "light.l", "n": "Lámpara", "a": "salon", "d": "light", "v": "Encendida", "t": "activo"}]}


def test_servicio_recibe_publica_acusa_y_refresca(kodi):
    srv = cargar("service").Servicio()
    srv.bucle()  # waitForAbort falso devuelve True: arranca, saluda y termina
    assert kodi.rpc[0]["params"] == {"sender": "service.ha_link", "message": "hola", "data": {"p": 1, "v": "0.1.0"}}
    srv.onNotification("otro", "Other.foto", json.dumps(FOTO))
    srv.onNotification("kodi_link", "Player.OnPlay", "{}")
    assert len(kodi.rpc) == 1  # se ignora lo que no es de HA
    srv.onNotification("kodi_link", "Other.foto", json.dumps(FOTO))
    vista = json.loads(kodi.props["ha_link.vista"])
    assert vista["estado"] == "al_dia" and vista["e"][0]["id"] == "light.l"
    assert kodi.rpc[-1]["params"]["message"] == "ok" and kodi.rpc[-1]["params"]["data"]["s"] == "s1"
    # el listado está abierto: se refresca
    kodi.ruta = "plugin://service.ha_link/?area=salon"
    srv.refrescado = 0
    srv.refrescar_si_abierto()
    assert kodi.builtins == ["Container.Refresh"]
    srv.onNotification("kodi_link", "Other.foto", "{roto")
    assert any("ilegible" in t for t in kodi.log)


def test_servicio_no_refresca_si_el_listado_no_esta_a_la_vista(kodi):
    srv = cargar("service").Servicio()
    srv.onNotification("kodi_link", "Other.foto", json.dumps(FOTO))
    kodi.ruta = "videodb://movies/"
    srv.refrescado = 0
    srv.refrescar_si_abierto()
    assert kodi.builtins == []


def _vista_publicada(kodi):
    srv = cargar("service").Servicio()
    srv.onNotification("kodi_link", "Other.foto", json.dumps(FOTO))


def test_plugin_raiz_y_area(kodi, monkeypatch):
    _vista_publicada(kodi)
    cargar("plugin", ["plugin://service.ha_link/", "7", "?modo=listado"], monkeypatch).main()
    etiquetas = [li.label for _, li, _ in kodi.items]
    assert etiquetas == ["Ahora mismo", "Salón"] and kodi.fin[-1]["cacheToDisc"] is False
    url_salon = kodi.items[1][0]
    assert url_salon == "plugin://service.ha_link/?area=salon" and kodi.items[1][2] is True
    kodi.items.clear()
    cargar("plugin", ["plugin://service.ha_link/", "7", "?area=salon"], monkeypatch).main()
    url, li, carpeta = kodi.items[0]
    assert li.label == "Lámpara" and "Encendida" in li.label2 and not carpeta
    assert li.art["icon"].endswith("resources/media/iconos/luz_activo.png") and os.path.exists(li.art["icon"])
    assert url == "plugin://service.ha_link/?ver=light.l"


def test_plugin_pulsar_entidad_avisa_solo_lectura(kodi, monkeypatch):
    _vista_publicada(kodi)
    cargar("plugin", ["plugin://service.ha_link/", "-1", "?ver=light.l"], monkeypatch).main()
    assert kodi.avisos[0][0] == "Lámpara" and kodi.avisos[0][1] == "Encendida · Solo lectura"
    assert kodi.items == []


def test_plugin_sin_servicio(kodi, monkeypatch):
    cargar("plugin", ["plugin://service.ha_link/", "7", "?modo=listado"], monkeypatch).main()
    assert [li.label for _, li, _ in kodi.items] == [L.TEXTOS["esperando"]]


def _foto_cfg(kodi, cfg):
    srv = cargar("service").Servicio()
    srv.onNotification("kodi_link", "Other.foto", json.dumps(dict(FOTO, cfg=cfg)))
    return srv


@pytest.mark.parametrize("pantalla", ["tablero", "filas"])
def test_plugin_raiz_abre_la_ventana_propia(kodi, monkeypatch, pantalla):
    _foto_cfg(kodi, {"vista": pantalla, "tecla": "ninguna"})
    cargar("plugin", ["plugin://service.ha_link/", "7", ""], monkeypatch).main()
    assert kodi.fin == [{"succeeded": False}] and kodi.items == []
    assert kodi.builtins[-1] == "RunScript(%s,%s)" % (os.path.join(ADDON, "ventana.py"), pantalla)


def test_plugin_raiz_con_listado_elegido_en_ha(kodi, monkeypatch):
    _foto_cfg(kodi, {"vista": "listado", "tecla": "ninguna"})
    cargar("plugin", ["plugin://service.ha_link/", "7", ""], monkeypatch).main()
    assert [li.label for _, li, _ in kodi.items] == ["Ahora mismo", "Salón"]


def test_servicio_mantiene_el_atajo_del_panel(kodi):
    ruta = "/perfil/keymaps/ha_link.xml"
    srv = _foto_cfg(kodi, {"vista": "tablero", "tecla": "azul"})
    assert "<blue>RunScript(%s,lateral)</blue>" % os.path.join(ADDON, "ventana.py") in kodi.ficheros[ruta]
    assert kodi.builtins == ["Action(reloadkeymaps)"]
    srv.publicar()  # sin cambios: no se reescribe ni se recargan las teclas
    assert kodi.builtins == ["Action(reloadkeymaps)"]
    srv.onNotification("kodi_link", "Other.foto", json.dumps(dict(FOTO, s="s2", cfg={"tecla": "ninguna"})))
    assert ruta not in kodi.ficheros and kodi.builtins[-1] == "Action(reloadkeymaps)"


def test_servicio_sin_datos_no_toca_el_atajo(kodi):
    kodi.ficheros["/perfil/keymaps/ha_link.xml"] = "<keymap/>"
    cargar("service").Servicio().bucle()
    assert kodi.ficheros["/perfil/keymaps/ha_link.xml"] == "<keymap/>"


def test_estan_todos_los_iconos():
    carpeta = os.path.join(ADDON, "resources", "media", "iconos")
    tipos = set(L.TIPOS.values()) | {"generico", "area", "ahora", "sin_conexion", "espera"}
    faltan = ["%s_%s.png" % (t, tono) for t in tipos for tono in L.TONOS
              if not os.path.exists(os.path.join(carpeta, "%s_%s.png" % (t, tono)))]
    assert faltan == []


def test_la_logica_no_importa_kodi():
    lib = os.path.join(ADDON, "resources", "lib", "ha_link")
    for nombre in os.listdir(lib):
        if nombre.endswith(".py"):
            texto = open(os.path.join(lib, nombre), encoding="utf-8").read()
            assert not re.search(r"^\s*(import|from)\s+xbmc", texto, re.M), nombre


def test_strings_po_al_dia():
    for carpeta in ("resource.language.es_es", "resource.language.en_gb"):
        texto = open(os.path.join(ADDON, "resources", "language", carpeta, "strings.po"), encoding="utf-8").read()
        ids = {int(x) for x in re.findall(r'msgctxt "#(\d+)"', texto)}
        assert ids == set(L.IDS.values()) | set(TB.IDS.values()), carpeta
    es = open(os.path.join(ADDON, "resources", "language", "resource.language.es_es", "strings.po"),
              encoding="utf-8").read()
    for textos, ids in ((L.TEXTOS, L.IDS), (TB.TEXTOS, TB.IDS)):
        for clave, ident in ids.items():
            assert 'msgctxt "#%d"\nmsgid' % ident in es and 'msgstr "%s"' % textos[clave] in es


def test_plugin_abrir_una_ventana_concreta(kodi, monkeypatch):
    cargar("plugin", ["plugin://service.ha_link/", "-1", "?abrir=lateral"], monkeypatch).main()
    assert kodi.builtins == ["RunScript(%s,lateral)" % os.path.join(ADDON, "ventana.py")] and kodi.fin == []


# --- pantalla de inicio del skin -------------------------------------------------------------------
def test_servicio_deja_revisiones_y_titulo_de_aqui(kodi):
    _foto_cfg(kodi, {"vista": "tablero", "tecla": "ninguna", "area": "salon", "area_n": "Salón"})
    assert kodi.props["ha_link.aqui"] == "Salón"
    assert all(len(kodi.props["ha_link.rev_%s" % f]) == 10 for f in ("ahora", "aqui", "estancias"))


def test_plugin_fila_de_estancias_abre_el_tablero_en_el_area(kodi, monkeypatch):
    _vista_publicada(kodi)
    cargar("plugin", ["plugin://service.ha_link/", "7", "?fila=estancias"], monkeypatch).main()
    url, li, carpeta = kodi.items[0]
    assert li.label == "Salón" and not carpeta and url == "plugin://service.ha_link/?abrir=tablero&area=salon"
    assert li.props["accion"] == "area" and os.path.exists(li.props["glifo"]) and os.path.exists(li.art["icon"])
    assert os.path.exists(li.props["bloque"]) and os.path.exists(li.props["halo"])


def test_plugin_fila_de_ahora_con_baldosas_de_k2(kodi, monkeypatch):
    _vista_publicada(kodi)
    cargar("plugin", ["plugin://service.ha_link/", "7", "?fila=ahora"], monkeypatch).main()
    url, li, _ = kodi.items[0]
    assert (li.label, li.label2) == ("Lámpara", "Salón") and url == "plugin://service.ha_link/?ver=light.l"
    for clave in ("bloque", "halo", "glifo"):
        assert os.path.exists(li.props[clave]), clave


def test_plugin_abrir_tablero_en_un_area_y_la_entrada_casa(kodi, monkeypatch):
    guion = os.path.join(ADDON, "ventana.py")
    cargar("plugin", ["plugin://service.ha_link/", "-1", "?abrir=tablero&area=cocina"], monkeypatch).main()
    assert kodi.builtins[-1] == "RunScript(%s,tablero,cocina)" % guion
    cargar("plugin", ["plugin://service.ha_link/", "-1", "?abrir=inicio"], monkeypatch).main()
    assert kodi.builtins[-1] == "RunScript(%s,tablero)" % guion  # sin datos: la pantalla por defecto
    _foto_cfg(kodi, {"vista": "listado", "tecla": "ninguna"})
    cargar("plugin", ["plugin://service.ha_link/", "-1", "?abrir=inicio"], monkeypatch).main()
    assert kodi.builtins[-1] == "ActivateWindow(Programs,plugin://service.ha_link/?modo=listado,return)"


def test_servicio_aviso_deja_el_aviso_y_abre_la_tarjeta_una_vez(kodi):
    srv = cargar("service").Servicio()
    aviso = {"p": 1, "id": "a1", "tipo": "timbre", "g": "importante", "ti": "Timbre", "m": "Puerta", "acc": "tarjeta"}
    srv.onNotification("kodi_link", "Other.aviso", json.dumps(aviso))
    assert json.loads(kodi.props["ha_link.aviso"])["id"] == "a1"
    assert kodi.builtins == ["RunScript(%s,aviso)" % os.path.join(ADDON, "ventana.py")]
    kodi.props["ha_link.aviso_abierto"] = "1"  # la tarjeta ya está a la vista: solo se cambia el aviso
    srv.onNotification("kodi_link", "Other.aviso", json.dumps(dict(aviso, id="a2")))
    assert json.loads(kodi.props["ha_link.aviso"])["id"] == "a2" and len(kodi.builtins) == 1
