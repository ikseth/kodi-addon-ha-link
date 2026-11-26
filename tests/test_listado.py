from ha_link import listado as L
from ha_link import receptor as R

AREAS = [{"id": "salon", "n": "Salón"}, {"id": "cocina", "n": "Cocina"}, {"id": "garaje", "n": "Garaje"}]


def e(eid, n, v, t, a="salon", c=None):
    d = {"id": eid, "n": n, "a": a, "d": eid.split(".")[0], "v": v, "t": t}
    if c:
        d["c"] = c
    return d


ENTIDADES = [
    e("light.lampara", "Lámpara", "Encendida", "activo"),
    e("sensor.temp", "Temperatura", "21,5 °C", "info", c="temperature"),
    e("binary_sensor.puerta", "Puerta", "Cerrada", "normal", c="door"),
    e("binary_sensor.humo", "Humo", "Detectado", "alerta", "cocina", "smoke"),
    e("scene.cine", "Cine", "", "info"),
    e("sensor.suelta", "Suelta", "3", "info", ""),
]


def vista(estado=R.AL_DIA, entidades=None, ultimo=1764170000):
    return {"p": 1, "estado": estado, "ultimo": ultimo, "areas": AREAS,
            "e": ENTIDADES if entidades is None else entidades}


def test_sin_datos():
    filas = L.raiz(None, 0)
    assert len(filas) == 1 and filas[0].etiqueta == L.TEXTOS["esperando"] and not filas[0].carpeta
    assert L.raiz(vista(R.SIN_DATOS), 0)[0].icono == "espera_nd.png"


def test_raiz_ahora_y_areas_en_orden_sin_las_vacias():
    filas = L.raiz(vista(), 0)
    assert [f.etiqueta for f in filas] == ["Ahora mismo", "Salón", "Cocina", "Sin área"]
    assert all(f.carpeta for f in filas)
    assert filas[0].destino == {"area": L.AHORA} and filas[1].destino == {"area": "salon"}
    assert filas[0].icono == "ahora_alerta.png" and filas[2].icono == "area_alerta.png"
    assert filas[1].icono == "area_activo.png"
    # resumen del salón: 1 activo y la temperatura, con color
    assert filas[1].etiqueta2 == "[COLOR FFFFB74D]1 activo[/COLOR]  ·  [COLOR FFFFFFFF]21,5 °C[/COLOR]"
    assert "1 alerta" in filas[0].etiqueta2 and "1 activo" in filas[0].etiqueta2
    assert filas[3].etiqueta2 == "[COLOR FF9E9E9E]1 elemento[/COLOR]"


def test_todo_en_calma():
    filas = L.raiz(vista(entidades=[e("sensor.temp", "T", "20 °C", "info", c="temperature")]), 0)
    assert filas[0].etiqueta2 == "[COLOR FF9E9E9E]Todo en calma[/COLOR]" and filas[0].icono == "ahora_normal.png"


def test_nada_expuesto():
    filas = L.raiz(vista(entidades=[]), 0)
    assert [f.etiqueta for f in filas] == [L.TEXTOS["nada_expuesto"]]


def test_area_en_orden_estable_con_color_e_icono():
    filas = L.area(vista(), "salon", 0)
    assert [f.etiqueta for f in filas] == ["Puerta", "Temperatura", "Lámpara", "Cine"]
    puerta, temp, lampara, cine = filas
    assert puerta.etiqueta2 == "[COLOR FF90A4AE]Cerrada[/COLOR]" and puerta.icono == "puerta_normal.png"
    assert temp.icono == "temperatura_info.png" and lampara.icono == "luz_activo.png"
    assert cine.etiqueta2 == "" and cine.icono == "escena_info.png"
    assert lampara.destino == {"ver": "light.lampara"} and not lampara.carpeta


def test_ahora_mismo_alertas_primero_y_con_el_area():
    filas = L.area(vista(), L.AHORA, 0)
    assert [f.entidad["id"] for f in filas] == ["binary_sensor.humo", "light.lampara"]
    assert filas[0].etiqueta == "Humo  [COLOR FF9E9E9E]Cocina[/COLOR]"


def test_caducado_avisa_y_apaga_los_colores():
    filas = L.raiz(vista(R.CADUCADO), 0)
    assert filas[0].icono == "sin_conexion_alerta.png" and "Sin conexión" in filas[0].etiqueta
    assert all(f.icono.endswith("_nd.png") for f in filas[1:])
    area = L.area(vista(R.CADUCADO), "salon", 0)
    assert area[0].icono == "sin_conexion_alerta.png"
    assert all("FF757575" in f.etiqueta2 for f in area[1:] if f.etiqueta2)


def test_textos_de_kodi_y_respaldo():
    filas = L.raiz(vista(), 0, {"ahora": "Right now", "activo_1": "1 active", "sin_area": ""})
    assert filas[0].etiqueta == "Right now" and "1 active" in filas[1].etiqueta2
    assert filas[-1].etiqueta == "Sin área"  # Kodi no lo dio: el incluido


def test_iconos_por_tipo_y_respaldo():
    assert L.icono("binary_sensor", "window", "activo") == "ventana_activo.png"
    assert L.icono("binary_sensor", "rara", "normal") == "binario_normal.png"
    assert L.icono("switch", "outlet", "activo") == "enchufe_activo.png"
    assert L.icono("vacuum", None, "info") == "generico_info.png"
    assert L.icono("light", None, "raro") == "luz_info.png"


def test_detalle():
    titulo, texto, icono = L.detalle(vista(), "light.lampara")
    assert titulo == "Lámpara" and texto == "Encendida · Solo lectura" and icono == "luz_activo.png"
    assert L.detalle(vista(), "scene.cine")[1] == "Solo lectura"
    assert L.detalle(vista(), "light.no_existe") is None
