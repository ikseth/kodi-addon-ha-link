"""Avisos en la tele (fase 3): de lo que manda HA a la tarjeta, y que existan sus imágenes y su ventana."""
import os

from ha_link import avisos as A
from ha_link import receptor as R
from ha_link import tablero as T

ADDON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "addon", "service.ha_link")
MEDIA = os.path.join(ADDON, "resources", "skins", "Default", "media", "k2")


def test_grave_que_pausa_es_roja_late_y_se_queda():
    a = A.normalizar({"p": 1, "id": "1", "tipo": "humo", "g": "grave", "ti": "Humo", "m": "Cocina", "acc": "pausar"})
    t = A.tarjeta(a)
    assert t["bloque"] == "bloque_alerta.png" and t["alerta"] == "1" and t["glifo"] == "glifos/smoke-detector-alert.png"
    assert t["fija"] == "1" and t["pista"] == T.TEXTOS["cerrar_aviso"]


def test_importante_ambar_y_aviso_gris_que_se_van_solos():
    imp = A.tarjeta(A.normalizar({"tipo": "timbre", "g": "importante", "ti": "Timbre", "acc": "tarjeta"}))
    assert imp["bloque"] == "bloque_activo.png" and imp["halo"] == "halo_activo.png" and imp["fija"] == ""
    normal = A.tarjeta(A.normalizar({"tipo": "raro", "g": "otra", "m": "Hola"}))
    assert normal["bloque"] == "bloque_reposo.png" and normal["glifo"] == "glifos/information-variant.png"
    assert normal["titulo"] == T.TEXTOS["aviso"] and normal["pista"] == ""


def test_lo_que_no_se_pinta_y_los_limites():
    assert A.normalizar({"ti": "", "m": "  "}) is None
    assert A.normalizar({"ti": "x", "acc": "nada"}) is None
    assert A.normalizar("roto") is None
    a = A.normalizar({"ti": "t" * 200, "m": "m" * 900, "d": 99999})
    assert len(a["ti"]) == A.MAX_TITULO and len(a["m"]) == A.MAX_MENSAJE and a["d"] == A.DURACION_MAX
    assert A.normalizar({"m": "x", "d": "nada"})["d"] == A.DURACION


def test_el_receptor_pasa_el_aviso_sin_tocar_la_vista():
    r = R.Receptor("0.3.0")
    salidas = r.recibir("aviso", {"p": R.PROTOCOLO, "m": "Hola"}, 100.0)
    assert salidas == [("aviso", {"p": R.PROTOCOLO, "m": "Hola"})] and r.ultimo is None
    assert r.recibir("aviso", {"p": 99, "m": "x"}, 100.0) == [("protocolo", 99)]


def test_estan_las_imagenes_y_la_ventana_del_aviso():
    for g in A.glifos_avisos():
        assert os.path.exists(os.path.join(MEDIA, "glifos", g + ".png")), g
    assert os.path.exists(os.path.join(ADDON, "resources", "skins", "Default", "1080i", "ha_link_aviso.xml"))
