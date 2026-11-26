"""Filas de la pantalla de inicio del skin: qué enseña cada una y cuándo cambia su revisión."""
from ha_link import inicio as I
from ha_link import tablero as T

from test_tablero import FUGA, HUM, LUZ, PUERTA, TEMP, TIRA, vista


def test_ahora_alertas_primero_y_con_el_area_debajo():
    v = vista(LUZ, TIRA, FUGA)
    assert [(b.entidad, b.linea2) for b in I.ahora(v)] == [("binary_sensor.fuga", "Cocina"), ("light.pie", "Salón")]


def test_ahora_en_reposo_y_sin_datos_dice_algo():
    tranquilo = I.ahora(vista(TIRA, PUERTA))
    assert len(tranquilo) == 1 and tranquilo[0].linea1 == T.TEXTOS["tranquilo"] and tranquilo[0].entidad is None
    espera = I.ahora(None)
    assert espera[0].linea1 == T.TEXTOS["esperando"] and espera[0].props["glifo"] == "glifos/timer-sand.png"


def test_aqui_son_las_entidades_del_area_de_este_kodi():
    v = vista(LUZ, TEMP, FUGA, cfg={"area": "salon", "area_n": "Salón"})
    assert {b.entidad for b in I.aqui(v)} == {"light.pie", "sensor.t"} and I.titulo_aqui(v) == "Salón"
    assert I.aqui(vista(LUZ)) == [] and I.titulo_aqui(vista(LUZ)) == ""
    assert I.aqui(vista(LUZ, cfg={"area": "garaje"})) == []
    assert I.titulo_aqui(vista(LUZ, cfg={"area": "garaje", "area_n": "Garaje"})) == ""  # sin nada, sin fila


def test_estancias_una_por_area_con_sus_indicadores():
    est = I.estancias(vista(LUZ, TEMP, FUGA, PUERTA))
    assert [b.entidad for b in est] == ["salon", "cocina", "entrada"]
    salon, cocina, entrada = est
    assert salon.props["accion"] == "area" and salon.props["glifo"] == "glifos/sofa.png" and salon.linea2 == "21,5°"
    assert salon.props["bloque"] == "bloque_activo.png" and salon.props["halo"] == "halo_activo.png"
    assert cocina.props["bloque"] == "bloque_alerta.png" and cocina.props["alerta"] == "1"
    assert entrada.props["bloque"] == "bloque_reposo.png" and entrada.props["glifo"] == "glifos/floor-plan.png"
    assert all(b.props["bloque"] == "bloque_nd.png" for b in I.estancias(vista(LUZ, FUGA, estado="caducado")))


def test_la_revision_solo_cambia_si_cambia_lo_que_se_ve():
    base = vista(LUZ, TEMP, HUM, cfg={"area": "cocina"})
    r0 = I.revisiones(base)
    # la humedad del salón no sale en «Estancias» (solo la temperatura) ni en «Ahora»; «Aquí» es la cocina
    assert I.revisiones(vista(LUZ, TEMP, dict(HUM, v="55 %"), cfg={"area": "cocina"})) == r0
    r1 = I.revisiones(vista(dict(LUZ, t="normal", v="Apagada"), TEMP, HUM, cfg={"area": "cocina"}))
    assert r1["ahora"] != r0["ahora"] and r1["estancias"] != r0["estancias"] and r1["aqui"] == r0["aqui"]
