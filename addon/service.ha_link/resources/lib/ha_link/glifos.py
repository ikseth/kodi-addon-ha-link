"""Qué glifo de Material Design Icons pinta cada cosa. Sin xbmc.

Lo usan el listado (K1, iconos ya coloreados), la ventana propia (K2, glifos blancos que Kodi tiñe) y los
generadores de herramientas/. Los glifos se descargan de @mdi/svg 7.4.47 (licencia en resources/media/iconos).
"""

# tipo: (glifo «encendido», glifo «apagado»). Activo, alerta e info usan el primero; normal y nd, el segundo:
# el icono cambia de forma, no solo de color (lenguaje visual aprobado, docs/diseno.md §7.1).
GLIFOS = {
    "puerta": ("door-open", "door-closed"),
    "garaje": ("garage-open-variant", "garage-variant"),
    "ventana": ("window-open-variant", "window-closed-variant"),
    "movimiento": ("motion-sensor", "motion-sensor-off"),
    "humo": ("smoke-detector-alert", "smoke-detector"),
    "agua": ("water-alert", "water-off"),
    "bateria": ("battery-alert", "battery"),
    "problema": ("alert-circle", "check-circle"),
    "red": ("lan-connect", "lan-disconnect"),
    "binario": ("checkbox-blank-circle", "checkbox-blank-circle-outline"),
    "temperatura": ("thermometer", "thermometer"),
    "humedad": ("water-percent", "water-percent"),
    "energia": ("flash", "flash-outline"),
    "sol": ("brightness-5", "brightness-5"),
    "reloj": ("clock-outline", "clock-outline"),
    "aire": ("air-filter", "air-filter"),
    "sensor": ("gauge", "gauge"),
    "luz": ("lightbulb-on", "lightbulb-outline"),
    "enchufe": ("power-plug", "power-plug-off"),
    "interruptor": ("toggle-switch", "toggle-switch-off-outline"),
    "ventilador": ("fan", "fan-off"),
    "automatismo": ("robot", "robot-off"),
    "escena": ("palette", "palette"),
    "script": ("script-text-play", "script-text"),
    "boton": ("gesture-tap-button", "gesture-tap-button"),
    "persiana": ("window-shutter-open", "window-shutter"),
    "candado": ("lock-open-variant", "lock"),
    "alarma": ("shield-lock", "shield-off-outline"),
    "clima": ("thermostat", "thermostat"),
    "tele": ("television", "television-off"),
    "persona": ("account", "account-outline"),
    "tiempo": ("weather-partly-cloudy", "weather-partly-cloudy"),
    "generico": ("information-outline", "information-outline"),
    "area": ("floor-plan", "floor-plan"),
    "ahora": ("lightning-bolt", "lightning-bolt"),
    "sin_conexion": ("lan-disconnect", "lan-disconnect"),
    "espera": ("timer-sand", "timer-sand"),
}
# excepciones por tono
ESPECIALES = {("alarma", "alerta"): "bell-ring"}

# Iconos de área que trae K2 (el «icon» del registro de áreas de HA). Uno que no esté aquí se pinta como «area».
AREAS = (
    "sofa", "sofa-single", "chef-hat", "stove", "silverware-fork-knife", "coffee", "fridge", "bed", "bed-king",
    "bed-double", "door", "door-open", "tree", "flower", "garage", "shower", "bathtub", "toilet", "desk", "laptop",
    "briefcase", "television", "gamepad-variant", "hanger", "washing-machine", "stairs", "home", "home-outline",
    "home-floor-1", "balcony", "pool", "car", "baby-carriage", "human-child", "teddy-bear", "wrench", "tools",
    "bookshelf", "office-building", "server", "router-wireless", "dumbbell", "music", "movie-open", "floor-plan",
)

# Glifos de la propia ventana (cabecera, avisos, teclas del mando).
INTERFAZ = (
    "home", "bell-ring", "check-circle-outline", "lan-connect", "lan-disconnect", "play", "thermometer",
    "arrow-left", "menu", "information-variant", "circle-medium", "pause", "timer-sand",
    # avisos (avisos.py): los que no salen ya en GLIFOS
    "weather-pouring", "shield-lock", "thermostat",
)


def glifo(tipo, tono):
    """Nombre MDI del glifo de un tipo en un tono (activo, alerta, info, normal, nd)."""
    if (tipo, tono) in ESPECIALES:
        return ESPECIALES[(tipo, tono)]
    encendido, apagado = GLIFOS.get(tipo) or GLIFOS["generico"]
    return encendido if tono in ("activo", "alerta", "info") else apagado


def glifo_area(icono):
    """El glifo del área; «sofa-outline» usa «sofa» (en la ventana los iconos de área van rellenos)."""
    if icono in AREAS:
        return icono
    base = (icono or "").replace("-outline", "")
    return base if base in AREAS else "floor-plan"


def todos():
    """Todos los glifos que necesita K2 (para el generador y las pruebas)."""
    nombres = set(AREAS) | set(INTERFAZ) | set(ESPECIALES.values())
    for encendido, apagado in GLIFOS.values():
        nombres.update((encendido, apagado))
    return sorted(nombres)
