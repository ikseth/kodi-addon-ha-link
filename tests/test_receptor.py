from ha_link import receptor as R

PUB = ("publicar",)


def foto(s="s1", n=1, t=1, e=None, areas=None, nivel="ve"):
    d = {"p": 1, "s": s, "n": n, "t": t, "nivel": nivel, "e": e or []}
    if n == 1:
        d["areas"] = areas or []
    return d


def ent(eid, v="x", t="info", a="salon"):
    return {"id": eid, "n": eid, "a": a, "d": eid.split(".")[0], "v": v, "t": t}


def test_saludo_al_arrancar():
    r = R.Receptor("0.1.0")
    assert r.saludo() == ("emitir", "hola", {"p": 1, "v": "0.1.0"})
    assert r.estado(0) == R.SIN_DATOS


def test_foto_en_una_parte_publica_y_acusa():
    r = R.Receptor("0.1.0")
    out = r.recibir("foto", foto(e=[ent("light.a")], areas=[{"id": "salon", "n": "Salón"}]), 100)
    assert out == [PUB, ("emitir", "ok", {"p": 1, "s": "s1", "v": "0.1.0", "n": 1})]
    v = r.vista(100)
    assert v["estado"] == R.AL_DIA and v["areas"] == [{"id": "salon", "n": "Salón"}] and len(v["e"]) == 1


def test_foto_por_partes_en_cualquier_orden():
    r = R.Receptor("v")
    assert r.recibir("foto", foto(n=2, t=3, e=[ent("light.b")]), 1) == []
    assert r.recibir("foto", foto(n=3, t=3, e=[ent("light.c")]), 1) == []
    assert r.estado(1) == R.SIN_DATOS
    out = r.recibir("foto", foto(n=1, t=3, e=[ent("light.a")], areas=[{"id": "x", "n": "X"}]), 1)
    assert PUB in out and out[-1][1] == "ok"
    assert sorted(r.entidades) == ["light.a", "light.b", "light.c"] and r.areas == [{"id": "x", "n": "X"}]


def test_foto_nueva_a_medias_no_mezcla_con_la_anterior():
    r = R.Receptor("v")
    r.recibir("foto", foto(s="s1", n=1, t=2, e=[ent("light.viejo")]), 1)
    r.recibir("foto", foto(s="s2", n=1, t=1, e=[ent("light.nuevo")]), 2)
    assert list(r.entidades) == ["light.nuevo"] and r.sesion == "s2"


def test_cambios_en_orden_y_quitar():
    r = R.Receptor("v")
    r.recibir("foto", foto(e=[ent("light.a", "Apagada"), ent("light.b")]), 1)
    assert r.recibir("cambio", {"p": 1, "s": "s1", "q": 1, "e": [ent("light.a", "Encendida", "activo")], "x": []},
                     2) == [PUB]
    assert r.entidades["light.a"]["v"] == "Encendida"
    assert r.recibir("cambio", {"p": 1, "s": "s1", "q": 2, "e": [], "x": ["light.b"]}, 3) == [PUB]
    assert list(r.entidades) == ["light.a"] and r.sec == 2


def test_hueco_en_la_secuencia_pide_foto_sin_insistir():
    r = R.Receptor("v")
    r.recibir("foto", foto(e=[ent("light.a")]), 1)
    out = r.recibir("cambio", {"p": 1, "s": "s1", "q": 3, "e": [ent("light.a", "otro")], "x": []}, 2)
    assert out == [("emitir", "pedir_foto", {"p": 1, "v": "v"})]
    assert r.entidades["light.a"]["v"] == "x"  # no se aplica
    assert r.recibir("cambio", {"p": 1, "s": "s1", "q": 4, "e": [], "x": []}, 5) == []  # antes de 10 s
    assert r.recibir("cambio", {"p": 1, "s": "s1", "q": 5, "e": [], "x": []}, 13)[0][1] == "pedir_foto"


def test_cambio_de_otra_sesion_pide_foto():
    r = R.Receptor("v")
    r.recibir("foto", foto(s="s1"), 1)
    assert r.recibir("cambio", {"p": 1, "s": "otra", "q": 1, "e": [], "x": []}, 2)[0][1] == "pedir_foto"


def test_latido_sin_foto_pide_foto():
    r = R.Receptor("v")
    assert r.recibir("latido", {"p": 1, "s": "s9", "q": 0}, 1)[0][1] == "pedir_foto"


def test_latido_detecta_cambios_perdidos():
    r = R.Receptor("v")
    r.recibir("foto", foto(), 1)
    assert r.recibir("latido", {"p": 1, "s": "s1", "q": 0}, 60) == []
    assert r.recibir("latido", {"p": 1, "s": "s1", "q": 2}, 120)[0][1] == "pedir_foto"


def test_caduca_sin_latidos_y_vuelve():
    r = R.Receptor("v")
    r.recibir("foto", foto(e=[ent("light.a")]), 0)
    assert r.revisar(100) == []
    assert r.revisar(R.CADUCA + 1) == [PUB]
    assert r.revisar(R.CADUCA + 5) == []  # solo una vez
    assert r.vista(R.CADUCA + 5)["estado"] == R.CADUCADO
    out = r.recibir("latido", {"p": 1, "s": "s1", "q": 0}, R.CADUCA + 10)
    assert out == [PUB] and r.estado(R.CADUCA + 10) == R.AL_DIA


def test_otro_protocolo_se_ignora():
    r = R.Receptor("v")
    assert r.recibir("foto", {"p": 2, "s": "s1", "n": 1, "t": 1, "e": [ent("light.a")]}, 1) == [("protocolo", 2)]
    assert r.estado(1) == R.SIN_DATOS


def test_basura_no_rompe():
    r = R.Receptor("v")
    assert r.recibir("foto", "texto", 1) == []
    assert r.recibir("desconocido", {"p": 1}, 1) == []
    assert r.recibir("foto", {"p": 1, "s": "s1", "n": 0, "t": 1}, 1) == []
    out = r.recibir("foto", {"p": 1, "s": "s1", "n": 1, "t": 1, "e": [None, {"sin_id": 1}, ent("light.a")]}, 1)
    assert PUB in out and list(r.entidades) == ["light.a"]


def test_adios_borra_los_datos():
    r = R.Receptor("v")
    r.recibir("foto", foto(e=[ent("light.a")]), 1)
    assert r.recibir("adios", {"p": 1}, 2) == [PUB]
    assert r.estado(2) == R.SIN_DATOS and r.vista(2)["e"] == []
