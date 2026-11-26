"""Modelo de la ventana propia (K2) y coherencia entre modelo, imágenes y ventanas XML."""
import os
import re

import pytest

from ha_link import glifos
from ha_link import tablero as T

ADDON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "addon", "service.ha_link")
MEDIA = os.path.join(ADDON, "resources", "skins", "Default", "media")
XML = os.path.join(ADDON, "resources", "skins", "Default", "1080i")

LUZ = {"id": "light.pie", "n": "Lámpara de pie", "a": "salon", "d": "light", "v": "Encendida", "t": "activo"}
TIRA = {"id": "light.tira", "n": "Tira LED", "a": "salon", "d": "light", "v": "Apagada", "t": "normal"}
TEMP = {"id": "sensor.t", "n": "Temperatura", "a": "salon", "d": "sensor", "c": "temperature", "v": "21,5 °C",
        "t": "info"}
HUM = {"id": "sensor.h", "n": "Humedad", "a": "salon", "d": "sensor", "c": "humidity", "v": "48 %", "t": "info"}
FUGA = {"id": "binary_sensor.fuga", "n": "Fuga de agua", "a": "cocina", "d": "binary_sensor", "c": "moisture",
        "v": "Húmedo", "t": "alerta"}
LAVAVAJILLAS = {"id": "switch.lv", "n": "Lavavajillas", "a": "cocina", "d": "switch", "v": "No disponible",
                "t": "nd"}
CINE = {"id": "scene.cine", "n": "Cine", "a": "salon", "d": "scene", "v": "", "t": "info"}
PUERTA = {"id": "binary_sensor.p", "n": "Puerta", "a": "entrada", "d": "binary_sensor", "c": "door",
          "v": "Cerrada", "t": "normal"}


def vista(*entidades, estado="al_dia", cfg=None):
    return {"p": 1, "estado": estado, "ultimo": 0, "nivel": "ve", "cfg": cfg or {},
            "areas": [{"id": "salon", "n": "Salón", "i": "sofa"}, {"id": "cocina", "n": "Cocina", "i": "chef-hat"},
                      {"id": "entrada", "n": "Entrada", "i": "icono-raro"}],
            "e": list(entidades)}


# --- baldosas ----------------------------------------------------------------------------------
def test_activo_bloque_ambar_con_halo_y_glifo_relleno():
    b = T.baldosa(LUZ)
    assert (b.linea1, b.linea2) == ("Lámpara de pie", "Encendida")
    assert b.props["bloque"] == "bloque_activo.png" and b.props["halo"] == "halo_activo.png"
    assert b.props["lavado"] == "lavado_activo.png" and b.props["glifo"] == "glifos/lightbulb-on.png"
    assert b.props["color_glifo"] == T.GLIFO["activo"] and b.props["clase"] == "estado"


def test_reposo_gris_con_glifo_de_contorno_y_sin_halo():
    b = T.baldosa(TIRA)
    assert b.props["bloque"] == "bloque_reposo.png" and b.props["halo"] == "" and b.props["lavado"] == ""
    assert b.props["glifo"] == "glifos/lightbulb-outline.png"


def test_alerta_late_y_no_disponible_lleva_marca():
    a = T.baldosa(FUGA)
    assert a.props["bloque"] == "bloque_alerta.png" and a.props["alerta"] == "1"
    assert a.props["glifo"] == "glifos/water-alert.png" and a.props["color_glifo"] == "FFFFFFFF"
    nd = T.baldosa(LAVAVAJILLAS)
    assert nd.props["bloque"] == "bloque_nd.png" and nd.props["nd"] == "1" and nd.props["alerta"] == ""


def test_valor_con_aro_en_escala():
    b = T.baldosa(TEMP)
    assert b.props["clase"] == "valor" and b.props["bloque"] == ""
    assert (b.props["valor"], b.props["unidad"]) == ("21,5", "°C")
    assert b.props["aro"] == "aro_12.png"  # (21,5 - 10) / 20 = 0,575 -> 11,5 -> 12 de 20
    assert b.props["color_aro"] == T.color_temperatura(21.5) == b.props["color_glifo"]
    assert (b.linea1, b.linea2) == ("21,5 °C", "Temperatura")
    h = T.baldosa(HUM)
    assert h.props["aro"] == "aro_10.png" and h.props["color_aro"] == T.CIAN


def test_valor_sin_escala_bloque_gris_con_glifo_cian():
    e = {"id": "sensor.lux", "n": "Luz exterior", "d": "sensor", "c": "illuminance", "v": "320 lx", "t": "info"}
    b = T.baldosa(e)
    assert b.props["aro"] == "" and b.props["bloque"] == "bloque_reposo.png" and b.props["color_glifo"] == T.CIAN


def test_escena_azul_de_contorno():
    b = T.baldosa(CINE)
    assert b.props["clase"] == "escena" and b.props["bloque"] == "bloque_escena.png"
    assert b.props["color_glifo"] == T.CIAN and b.linea1 == "Cine"


def test_caducado_sin_color_pero_con_la_forma_del_estado():
    b = T.baldosa(LUZ, caducado=True)
    assert b.props["bloque"] == "bloque_reposo.png" and b.props["halo"] == ""
    assert b.props["glifo"] == "glifos/lightbulb-on.png"  # sigue diciendo «encendida» por la forma
    assert T.baldosa(TEMP, caducado=True).props["aro"] == ""


@pytest.mark.parametrize("v,esperado", [
    ("21,5 °C", (21.5, "21,5", "°C")), ("-3 °C", (-3.0, "-3", "°C")), ("48 %", (48.0, "48", "%")),
    ("1.2 kW", (1.2, "1.2", "kW")), ("Abierta", (None, "Abierta", "")), ("", (None, "", "")),
])
def test_partir_valor(v, esperado):
    assert T.partir_valor(v) == esperado


def test_aros_en_sus_limites():
    assert T.aro("temperature", 5, "°C")[0] == "aro_00.png"
    assert T.aro("temperature", 40, "°C")[0] == "aro_20.png"
    assert T.aro("power", 1.5, "kW")[0] == "aro_20.png"
    assert T.aro("power", 250, "W")[0] == "aro_05.png"
    assert T.aro("battery", 15, "%")[1] == T.color_bateria(15) != T.color_bateria(80)
    assert T.aro("illuminance", 300, "lx") is None


# --- áreas e indicadores ------------------------------------------------------------------------
def test_areas_ahora_primero_y_en_el_orden_de_ha():
    areas = T.areas(vista(LUZ, TIRA, TEMP, FUGA, PUERTA))
    assert [a.id for a in areas] == [T.AHORA, "salon", "cocina", "entrada"]
    ahora = areas[0]
    assert [b.entidad for b in ahora.baldosas] == ["binary_sensor.fuga", "light.pie"]  # alertas primero
    assert ahora.baldosas[0].linea2 == "Cocina"  # en «Ahora mismo», el área en lugar del estado
    assert ahora.props["glifo"] == "glifos/bell-ring.png"


def test_indicadores_de_area():
    salon = T.areas(vista(LUZ, TIRA, TEMP))[1]
    p = salon.props
    assert p["glifo"] == "glifos/sofa.png"
    assert (p["ind1"], p["ind1_glifo"], p["ind2"]) == ("circulo_activo.png", "glifos/lightbulb-on.png", "")
    assert p["n_ind"] == "1" and p["temp"] == "21,5°" and p["temp_color"] == T.color_temperatura(21.5)
    assert p["tranquilo"] == ""
    entrada = T.areas(vista(PUERTA))[0]
    assert entrada.props["tranquilo"] == "1" and entrada.props["glifo"] == "glifos/floor-plan.png"  # icono no traído
    cocina = [a for a in T.areas(vista(FUGA, LAVAVAJILLAS)) if a.id == "cocina"][0]
    assert cocina.props["ind1"] == "circulo_alerta.png" and cocina.props["ind1_color"] == "FFFFFFFF"


def test_como_mucho_tres_indicadores():
    luces = [dict(LUZ, id="light.%d" % i, n="Luz %d" % i) for i in range(5)]
    p = T.areas(vista(*luces))[1].props
    assert p["n_ind"] == "3" and p["ind3"] == "circulo_activo.png"


def test_sin_datos_y_nada_expuesto():
    assert T.areas(None) == [] and T.areas({"estado": "sin_datos"}) == []
    assert T.aviso(None) == T.TEXTOS["esperando"]
    assert T.aviso(vista()) == T.TEXTOS["nada"]
    assert T.aviso(vista(LUZ)) == ""


def test_cabecera_segun_el_estado():
    assert T.cabecera(vista(LUZ))["estado"] == "Al día"
    c = T.cabecera(dict(vista(LUZ), estado="caducado", ultimo=None))
    assert c["estado"] == "Datos de las --:--" and c["estado_glifo"] == "glifos/lan-disconnect.png"
    assert T.cabecera(None)["estado_glifo"] == "glifos/timer-sand.png"


# --- panel lateral ----------------------------------------------------------------------------------
def test_lateral_ahora_y_el_area_del_kodi():
    v = vista(LUZ, TIRA, TEMP, FUGA, CINE, cfg={"area": "salon", "area_n": "Salón"})
    titulo, ahora, titulo_aqui, aqui = T.lateral(v)
    assert titulo == "Casa" and titulo_aqui == "Salón"
    assert [b.entidad for b in ahora] == ["binary_sensor.fuga", "light.pie"]
    assert {b.entidad for b in aqui} == {"light.pie", "light.tira", "sensor.t", "scene.cine"}


def test_lateral_sin_area_ahora_ocupa_todo():
    luces = [dict(LUZ, id="light.%d" % i) for i in range(12)]
    _, ahora, titulo_aqui, aqui = T.lateral(vista(*luces))
    assert titulo_aqui == "" and aqui == [] and len(ahora) == T.MAX_AHORA_LATERAL + T.MAX_AQUI_LATERAL


def test_mapa_de_teclas():
    xml = T.mapa_teclas("roja", "/addons/service.ha_link/ventana.py")
    assert "<FullscreenVideo>" in xml and "<red>RunScript(/addons/service.ha_link/ventana.py,lateral)</red>" in xml
    assert T.mapa_teclas("ninguna", "x") is None and T.mapa_teclas(None, "x") is None


# --- imágenes y ventanas -------------------------------------------------------------------------
def test_estan_todas_las_imagenes():
    faltan = [g for g in glifos.todos() if not os.path.exists(os.path.join(MEDIA, "k2", "glifos", g + ".png"))]
    fijas = set(T.BLOQUE.values()) | {"halo_activo.png", "halo_alerta.png", "lavado_activo.png", "lavado_alerta.png",
                                      "circulo_activo.png", "circulo_alerta.png", "aro_pista.png"}
    fijas |= {"aro_%02d.png" % i for i in range(T.PASOS_ARO + 1)}
    for nombre in os.listdir(XML):
        fijas |= set(re.findall(r"k2/([\w/.-]+\.png)", open(os.path.join(XML, nombre), encoding="utf-8").read()))
    faltan += [f for f in fijas if not os.path.exists(os.path.join(MEDIA, "k2", f))]
    assert faltan == []


def test_todos_los_tipos_tienen_glifo():
    from ha_link import listado
    assert set(listado.TIPOS.values()) <= set(glifos.GLIFOS)


def test_ids_de_las_ventanas_coinciden_con_ventana_py():
    texto = open(os.path.join(ADDON, "ventana.py"), encoding="utf-8").read()
    ids = {
        "ha_link_tablero.xml": ("AREAS", "BALDOSAS"),
        "ha_link_filas.xml": ("PRIMERA_FILA",),
        "ha_link_lateral.xml": ("AHORA_1", "AHORA_3", "AQUI"),
    }
    for fichero, nombres in ids.items():
        xml = open(os.path.join(XML, fichero), encoding="utf-8").read()
        for nombre in nombres:
            valor = re.search(r"\b%s\b[^=\n]*=\s*([\d, ]+)" % nombre, texto)
            assert valor, nombre
            numeros = [int(x) for x in valor.group(1).split(",") if x.strip()]
            posicion = [n.strip() for n in re.search(r"([\w, ]+)\s*=\s*[\d, ]+\n", texto[valor.start():]).group(1)
                        .split(",")].index(nombre)
            assert 'id="%d"' % numeros[posicion] in xml, (fichero, nombre)
    filas = open(os.path.join(XML, "ha_link_filas.xml"), encoding="utf-8").read()
    assert all('id="%d"' % (301 + i) in filas for i in range(T.MAX_FILAS))


def test_icono_de_area_de_contorno_usa_el_relleno():
    assert glifos.glifo_area("sofa-outline") == "sofa" and glifos.glifo_area("bed-king-outline") == "bed-king"
    assert glifos.glifo_area("sofa") == "sofa" and glifos.glifo_area("rocket-outline") == "floor-plan"
    assert glifos.glifo_area(None) == "floor-plan"


@pytest.mark.parametrize("nombre,area,esperado", [
    ("Ventana del salón", "Salón", "Ventana"),
    ("Temperatura del dormitorio principal", "Dormitorio Principal", "Temperatura"),
    ("Puerta de la entrada", "Entrada", "Puerta"),
    ("Salón Lámpara", "Salón", "Lámpara"),
    ("Puerta principal", "Entrada", "Puerta principal"),
    ("Salón", "Salón", "Salón"),
    ("Lámpara", None, "Lámpara"),
])
def test_sin_area(nombre, area, esperado):
    assert T.sin_area(nombre, area) == esperado


def test_el_area_se_quita_del_nombre_en_las_baldosas():
    v = vista(dict(TEMP, n="Temperatura del salón"), dict(LUZ, n="Lámpara de pie del salón"),
              cfg={"area": "salon", "area_n": "Salón"})
    salon = T.areas(v)[1]
    assert {b.linea2 for b in salon.baldosas if b.props["clase"] == "valor"} == {"Temperatura"}
    assert T.areas(v)[0].baldosas[0].linea1 == "Lámpara de pie"  # también en «Ahora mismo»
    assert {b.linea1 for b in T.lateral(v)[3]} >= {"Lámpara de pie"}
