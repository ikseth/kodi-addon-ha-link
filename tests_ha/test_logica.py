"""Lógica pura de kodi_link (sin Home Assistant)."""
import importlib.util
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

RUTA = os.path.join(os.path.dirname(__file__), "..", "custom_components", "kodi_link", "logica.py")
_spec = importlib.util.spec_from_file_location("logica_kodi_link", RUTA)
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

TZ = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 26, 18, 0, tzinfo=TZ)
TRAD = {
    "component.binary_sensor.entity_component.door.state.on": "Abierta",
    "component.binary_sensor.entity_component._.state.on": "Encendido",
    "component.light.entity_component._.state.off": "Apagada",
    "component.demo.entity.sensor.modo.state.eco": "Ahorro",
}


def desc(eid, estado, **kw):
    kw.setdefault("nombre", "Cosa")
    kw.setdefault("area_id", "salon")
    kw.setdefault("area_nombre", "Salón")
    return L.describir(entity_id=eid, estado=estado, idioma="es", traducciones=TRAD, zona=TZ, ahora=AHORA, **kw)


def test_puerta_abierta_es_activo_y_traducida():
    d = desc("binary_sensor.puerta", "on", clase="door", nombre="Puerta de la entrada")
    assert d == {"id": "binary_sensor.puerta", "n": "Puerta de la entrada", "a": "salon", "d": "binary_sensor",
                 "v": "Abierta", "t": L.ACTIVO, "c": "door"}


def test_humo_detectado_es_alerta():
    assert desc("binary_sensor.humo", "on", clase="smoke")["t"] == L.ALERTA
    assert desc("binary_sensor.humo", "off", clase="smoke")["t"] == L.NORMAL


def test_no_disponible():
    d = desc("sensor.t", "unavailable", clase="temperature", unidad="°C")
    assert d["t"] == L.NO_DISPONIBLE and d["v"] == "No disponible"


def test_numero_con_precision_y_coma():
    assert desc("sensor.t", "21.53", clase="temperature", unidad="°C", precision=1)["v"] == "21,5 °C"
    assert desc("sensor.h", "45", unidad="%")["v"] == "45 %"
    assert desc("sensor.p", "1234.5678", unidad="W")["v"] == "1234,57 W"
    assert desc("sensor.c", "-0.04", unidad="°C", precision=1)["v"] == "0,0 °C"
    assert L.numero("21.5", None, "en") == "21.5"
    assert L.numero("abc", 1, "es") is None


def test_sensor_de_texto_usa_la_traduccion_de_su_integracion():
    d = desc("sensor.modo", "eco", plataforma="demo", clave_traduccion="modo")
    assert d["v"] == "Ahorro" and d["t"] == L.INFO


def test_marca_de_tiempo_en_hora_local():
    assert desc("sensor.ultima", "2026-11-26T16:05:00+00:00", clase="timestamp")["v"] == "17:05"
    assert desc("sensor.ultima", "2026-11-24T16:05:00+00:00", clase="timestamp")["v"] == "24/11 17:05"


def test_genericos_y_traduccion_por_defecto():
    assert desc("light.l", "off")["v"] == "Apagada"
    assert desc("light.l", "on")["v"] == "Encendido"  # sin traducción del componente: texto genérico
    assert desc("cover.p", "open")["t"] == L.ACTIVO
    assert desc("scene.cine", "2026-11-26T10:00:00+00:00")["v"] == ""


def test_actuable_y_nivel():
    d = desc("light.l", "on", actuable=True)
    assert d["ac"] == 1
    assert "ac" not in L.con_nivel(d, False)
    assert L.con_nivel(d, True) is d


def test_nombre_sin_el_area():
    assert L.nombre_corto("Salón Temperatura", "Salón") == "Temperatura"
    assert L.nombre_corto("salón - lámpara", "Salón") == "Lámpara"
    assert L.nombre_corto("Salón", "Salón") == "Salón"
    assert L.nombre_corto("Puerta", None) == "Puerta"


def test_areas_en_el_orden_de_la_ui():
    areas = [("cocina", "Cocina", "baja"), ("dormitorio", "Dormitorio", "alta"), ("garaje", "Garaje", None),
             ("salon", "Salón", "baja"), ("trastero", "Trastero", "baja")]
    res = L.ordenar_areas(areas, ["alta", "baja"], {"cocina", "dormitorio", "garaje", "salon"})
    assert [a["id"] for a in res] == ["dormitorio", "cocina", "salon", "garaje"]


def test_diferencias():
    a = {"x": {"id": "x", "v": "1"}, "y": {"id": "y", "v": "1"}}
    b = {"x": {"id": "x", "v": "2"}, "z": {"id": "z", "v": "1"}}
    cambiadas, quitadas = L.diferencias(a, b)
    assert sorted(d["id"] for d in cambiadas) == ["x", "z"] and quitadas == ["y"]


def _muchas(n):
    return [desc(f"sensor.temperatura_numero_{i:04d}", "21.5", unidad="°C", nombre=f"Temperatura {i}")
            for i in range(n)]


def test_foto_pequena_en_una_parte():
    partes = L.mensajes_foto("s1", [{"id": "salon", "n": "Salón"}], _muchas(3), "ve")
    assert len(partes) == 1 and partes[0]["n"] == 1 and partes[0]["t"] == 1
    assert partes[0]["areas"] == [{"id": "salon", "n": "Salón"}] and len(partes[0]["e"]) == 3


def test_foto_vacia_tiene_una_parte():
    partes = L.mensajes_foto("s1", [], [], "ve")
    assert len(partes) == 1 and partes[0]["e"] == [] and partes[0]["t"] == 1


def test_foto_grande_troceada_por_debajo_del_limite():
    entidades = _muchas(1500)
    partes = L.mensajes_foto("s1", [{"id": "salon", "n": "Salón"}], entidades, "ve")
    assert len(partes) > 1
    assert all(p["t"] == len(partes) for p in partes)
    assert [p["n"] for p in partes] == list(range(1, len(partes) + 1))
    assert "areas" in partes[0] and all("areas" not in p for p in partes[1:])
    assert sum(len(p["e"]) for p in partes) == 1500
    for p in partes:
        assert len(L.peticion("foto", p, "kodi_link", 123456).encode("utf-8")) < L.LIMITE + 200 < 32 * 1024


def test_cambios_troceados():
    lotes = L.lotes_cambio(_muchas(1500), ["sensor.quitada"])
    assert len(lotes) > 1
    assert sum(len(e) for e, _ in lotes) == 1500 and lotes[-1][1] == ["sensor.quitada"]
    for e, x in lotes:
        datos = {"p": 1, "s": "abcdefabcdef", "q": 12345, "e": e, "x": x}
        assert len(L.peticion("cambio", datos, "kodi_link", 123456).encode("utf-8")) < 32 * 1024


def test_peticion_es_json_rpc():
    m = json.loads(L.peticion("foto", {"a": "ñ"}, "kodi_link", 7))
    assert m == {"jsonrpc": "2.0", "id": 7, "method": "JSONRPC.NotifyAll",
                 "params": {"sender": "kodi_link", "message": "foto", "data": {"a": "ñ"}}}


def test_icono_del_area_y_cfg_en_la_primera_parte():
    areas = [("salon", "Salón", None, "mdi:sofa"), ("cocina", "Cocina", None, None), ("jardin", "Jardín", None, "hass:tree")]
    assert L.ordenar_areas(areas, [], {"salon", "cocina", "jardin"}) == [
        {"id": "salon", "n": "Salón", "i": "sofa"}, {"id": "cocina", "n": "Cocina"}, {"id": "jardin", "n": "Jardín"}]
    cfg = {"vista": "tablero", "tecla": "azul"}
    partes = L.mensajes_foto("s1", [{"id": "salon", "n": "Salón"}], _muchas(3), "ve", cfg=cfg)
    assert partes[0]["cfg"] == cfg and all("cfg" not in p for p in partes[1:])
    assert all(L.tamano(L.peticion("foto", p, "kodi_link", 1)) <= L.LIMITE for p in partes)
