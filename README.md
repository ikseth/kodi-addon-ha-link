# kodi-addon-ha-link

Canal entre **Home Assistant** y **Kodi**: paneles con información y acciones mínimas de la casa dentro de la
interfaz de Kodi, notificaciones y eventos (timbre, puertas, alarma) que cada Kodi trata según su configuración.

Tiene dos mitades, las dos instalables y configurables desde su interfaz:
- Una **integración de Home Assistant** (`custom_components/kodi_link`): qué se expone (etiquetas `Kodi: ve` y
  `Kodi: actúa`), qué Kodi participan, con qué nivel y qué paneles ven.
- Un **addon de Kodi** que pinta los datos y devuelve las pulsaciones. No guarda credenciales: el control de acceso
  lo aplica Home Assistant.

Requisitos: Kodi 21 o posterior y la integración Kodi de Home Assistant.

Estado: fase 1 (solo lectura) terminada en 0.2.0 y validada en un Kodi real: listado, tablero por áreas, filas por
estancia y panel lateral durante la reproducción. Ver
[docs/diseno.md](docs/diseno.md), [docs/protocolo.md](docs/protocolo.md) y [docs/fase0-resultados.md](docs/fase0-resultados.md).

## Instalación

- **Home Assistant:** copiar `custom_components/kodi_link` en la carpeta `custom_components` de HA, reiniciar y añadir **Kodi Link** en *Ajustes → Dispositivos y servicios*. Las etiquetas que se dejen en
  blanco se crean solas («Kodi: ve» y «Kodi: actúa»). Después, *Añadir Kodi* en la propia integración, con su nivel,
  la pantalla que abre (tablero por áreas, filas por estancia o listado) y la tecla del mando que muestra el panel
  lateral durante la reproducción.
- **Kodi:** el zip de la [última release](https://github.com/ikseth/kodi-addon-ha-link/releases/latest) (o uno propio
  con `./build_zip.sh`, que lo deja en `dist/addon/`) y, en Kodi, *Complementos → Instalar desde un archivo zip*. Para
  actualizar, el zip de la versión nueva por el mismo camino. Se abre en *Complementos → Programas → HA Link*; el panel lateral, con
  la tecla elegida en HA mientras se ve un vídeo.

## Estructura

| Ruta | Qué es |
|---|---|
| `custom_components/kodi_link/` | Integración de HA. `logica.py` es puro (sin HA) |
| `addon/service.ha_link/` | Addon de Kodi: `service.py` (canal y atajo del mando), `plugin.py` (entrada y listado) y `ventana.py` (ventana propia), capas finas sobre `resources/lib/ha_link/` (sin `xbmc`) |
| `addon/service.ha_link/resources/skins/Default/` | Ventanas XML y sus imágenes (generadas, no se editan a mano) |
| `tests/` | Pruebas del addon (con módulos `xbmc*` falsos para las capas finas) |
| `tests_ha/` | Pruebas de la integración (`pytest-homeassistant-custom-component`, con un Kodi falso por WebSocket) |
| `herramientas/` | Generadores de `strings.po`, de los iconos del listado y de las imágenes y ventanas de K2 (Material Design Icons) |
| `estuary/` | Include de las filas de inicio para un clon de Estuary (generado; lo usa el parche de Estuary Adviser) |
| `fase0/` | Prueba de canal de la fase 0 (histórico) |

Pruebas: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests tests_ha`, en un entorno con
`pytest-homeassistant-custom-component`.

## Licencia

MIT (`LICENSE`). Los iconos son de [Material Design Icons](https://pictogrammers.com/library/mdi/) (Apache 2.0,
`addon/service.ha_link/resources/media/iconos/LICENSE-MDI.txt`).
