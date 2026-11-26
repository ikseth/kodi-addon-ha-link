"""Lo que llega de Home Assistant: foto por partes, cambios con secuencia, latido y adiós.

Sin xbmc. El servicio le pasa cada mensaje y hace lo que devuelve:
  ("publicar",)               la vista ha cambiado: publicarla para el listado
  ("emitir", mensaje, datos)  mandar a HA con JSONRPC.NotifyAll
  ("protocolo", version)      HA habla otra versión del protocolo: avisar en el log
Contrato en docs/protocolo.md.
"""

PROTOCOLO = 1
CADUCA = 150  # s sin noticias de HA (el latido es cada 60 s): los datos se marcan como antiguos
PEDIR_CADA = 10  # s como mínimo entre dos peticiones de foto

SIN_DATOS = "sin_datos"
AL_DIA = "al_dia"
CADUCADO = "caducado"

PUBLICAR = ("publicar",)


class Receptor(object):

    def __init__(self, version):
        self.version = version
        self.sesion = None
        self.sec = 0
        self.nivel = None
        self.areas = []
        self.cfg = {}  # configuración de este Kodi en HA: pantalla, tecla del panel, su área
        self.entidades = {}
        self.ultimo = None  # última noticia de HA (time.time())
        self._foto = None  # foto a medio llegar: {"s", "t", "partes"}
        self._pedida = None
        self._caducado = False

    # --- mensajes de HA -----------------------------------------------------------------
    def recibir(self, mensaje, datos, ahora):
        if mensaje not in ("foto", "cambio", "latido", "adios"):
            return []
        if not isinstance(datos, dict):
            return []
        if datos.get("p") != PROTOCOLO:
            return [("protocolo", datos.get("p"))]
        self.ultimo = ahora
        salidas = []
        if self._caducado:
            self._caducado = False
            salidas.append(PUBLICAR)
        if mensaje == "foto":
            return self._parte(datos, ahora, salidas)
        if mensaje == "cambio":
            return self._cambio(datos, ahora, salidas)
        if mensaje == "latido":
            if datos.get("s") != self.sesion or datos.get("q") != self.sec:
                salidas += self._pedir(ahora)
            return salidas
        # adiós: este Kodi deja de recibir datos
        self.sesion, self.sec, self.nivel, self.areas, self.entidades = None, 0, None, [], {}
        self.cfg = {}
        self._foto = None
        self.ultimo = None
        return _con_publicar(salidas)

    def _parte(self, datos, ahora, salidas):
        s, n, t = datos.get("s"), datos.get("n"), datos.get("t")
        if not s or not isinstance(n, int) or not isinstance(t, int) or not 1 <= n <= t:
            return salidas
        if self._foto is None or self._foto["s"] != s or self._foto["t"] != t:
            self._foto = {"s": s, "t": t, "partes": {}}
        self._foto["partes"][n] = datos
        partes = self._foto["partes"]
        if len(partes) < t:
            return salidas
        self.areas = list(partes[1].get("areas") or [])
        self.cfg = dict(partes[1].get("cfg") or {})
        self.entidades = {}
        for i in range(1, t + 1):
            for e in partes[i].get("e") or []:
                if isinstance(e, dict) and e.get("id"):
                    self.entidades[e["id"]] = e
        self.sesion, self.sec, self.nivel = s, 0, datos.get("nivel")
        self._foto = None
        salidas = _con_publicar(salidas)
        salidas.append(("emitir", "ok", {"p": PROTOCOLO, "s": s, "v": self.version, "n": len(self.entidades)}))
        return salidas

    def _cambio(self, datos, ahora, salidas):
        if datos.get("s") != self.sesion or datos.get("q") != self.sec + 1:
            return salidas + self._pedir(ahora)  # nos hemos perdido algo: foto nueva
        for e in datos.get("e") or []:
            if isinstance(e, dict) and e.get("id"):
                self.entidades[e["id"]] = e
        for x in datos.get("x") or []:
            self.entidades.pop(x, None)
        self.sec = datos["q"]
        return _con_publicar(salidas)

    def _pedir(self, ahora):
        if self._pedida is not None and ahora - self._pedida < PEDIR_CADA:
            return []
        self._pedida = ahora
        return [("emitir", "pedir_foto", {"p": PROTOCOLO, "v": self.version})]

    # --- al arrancar y con el paso del tiempo ---------------------------------------------
    def saludo(self):
        """Al arrancar el servicio: si HA ya está conectado, contesta con la foto."""
        return ("emitir", "hola", {"p": PROTOCOLO, "v": self.version})

    def revisar(self, ahora):
        """Llamar cada pocos segundos: avisa cuando los datos pasan a estar caducados."""
        if self.sesion is not None and not self._caducado and self.estado(ahora) == CADUCADO:
            self._caducado = True
            return [PUBLICAR]
        return []

    def estado(self, ahora):
        if self.sesion is None:
            return SIN_DATOS
        if self.ultimo is None or ahora - self.ultimo > CADUCA:
            return CADUCADO
        return AL_DIA

    def vista(self, ahora):
        """Lo que lee el listado (va en una propiedad de la ventana Home)."""
        return {"p": PROTOCOLO, "estado": self.estado(ahora), "ultimo": self.ultimo, "nivel": self.nivel,
                "cfg": self.cfg, "areas": self.areas, "e": list(self.entidades.values())}


def _con_publicar(salidas):
    return salidas if PUBLICAR in salidas else salidas + [PUBLICAR]
