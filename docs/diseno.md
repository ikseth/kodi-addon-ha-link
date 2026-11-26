# Panel y canal de Home Assistant en Kodi: diseño

Estado: **diseño aprobado en lo esencial** (26/11/2026). Fase 0 hecha: el canal funciona
([fase0-resultados.md](fase0-resultados.md)). **Fase 1 terminada en 0.2.0** (solo lectura): integración, listado y
K2 (A, B y C, lenguaje visual en §7.1), validados en la tele en el piloto de la instalación de referencia (26/11). Contrato entre las dos mitades:
[protocolo.md](protocolo.md). Nombre: `kodi-addon-ha-link`, con la integración `kodi_link`.

## 1. Lo que se quiere

1. **En todos los Kodi.**
2. **Información y acciones mínimas, no críticas**: puertas, temperaturas, encender o apagar algo, lanzar una escena.
3. **Lo que se expone lo decide HA con etiquetas.**
4. **Eventos configurables en cada Kodi**: mostrar notificaciones o no, y parar la reproducción ante ciertas alertas.
5. **HA manda datos y Kodi los pinta.**
6. **Todo instalable y configurable**, en las dos mitades: nada de piezas sueltas montadas a mano.
7. **Configuración compartida** entre los Kodi, para no reconfigurar cada uno, siempre que se justifique.
8. **Sustituye a las notificaciones actuales a los Kodi**, con un canal propio de la integración.

Condiciones de partida:
- **Kodi 21 Omega o posterior (Python 3).** La instalación de referencia no tiene ningún Leia (D8).
- Módulo sin datos de ninguna instalación concreta.
- Local, sin nube.

## 2. Decisiones tomadas (26/11)

| # | Decisión |
|---|---|
| D1 | **Integración de HA más addon de Kodi** (opción B). Sin credenciales en Kodi. HA aplica el control de acceso. |
| D2 | **Dos etiquetas:** `Kodi: ve` (solo lectura) y `Kodi: actúa` (se puede accionar). |
| D3 | **Primero el listado** (K1): sirve para ver qué se expone y cómo se usa antes de diseñar paneles. |
| D4 | **Canal de notificaciones propio** en la integración, que sustituye a los envíos actuales a los Kodi. |
| D5 | **Las dos mitades se instalan y se configuran desde su interfaz:** la integración desde *Dispositivos y servicios* y el addon desde un zip o un repositorio de Kodi. |
| D6 | **Paneles definidos en HA más edición rápida desde Kodi** (§5). Puede ser limitada, pero **la estética y la experiencia de uso tienen que ser potentes**: el pintado se diseña con maquetas antes de programarlo. |
| D7 | Nombre: **`kodi-addon-ha-link`**, con la integración `kodi_link`. |
| D8 | **Solo Kodi 21 o posterior (Python 3).** Sin variante Leia: permite usar todo lo visual de Kodi 21. |
| D9 | **Mensajes de menos de 32 KB** y estado por cambios: el WebSocket de Kodi corta la conexión por encima de 64 KB (fase 0). Las imágenes van por HTTP, no por el canal. |

## 3. Arquitectura (opción B)

Es el mismo patrón que `kodi-addon-parental` (`kodi_parental`):

- **Integración de HA** (`custom_components/`, configuración por la UI):
  - **Entrada principal:** las etiquetas y los ajustes comunes.
  - **Subentrada «Kodi»**, una por equipo: qué `media_player` de la integración Kodi es, con qué **nivel**
    (§4) y qué **paneles** (§5).
- **Addon de Kodi** (`service.*` más una parte de plugin para el listado): pinta, recibe los eventos y envía las
  pulsaciones.
- **Canal:**
  - HA → Kodi por `JSONRPC.NotifyAll` (estados, paneles, eventos y configuración).
  - Kodi → HA por una notificación JSON-RPC que la integración recibe por su conexión WebSocket con el Kodi. HA
    **valida cada acción** (etiqueta, nivel del Kodi y dominio permitido) antes de ejecutarla.

## 4. Quién ve qué (punto 4 del propietario)

**El control de acceso va por Kodi y lo decide HA**, con independencia de cómo se definan los paneles. Cada subentrada
«Kodi» tiene un nivel:

| Nivel | Qué recibe ese Kodi |
|---|---|
| Nada | Ni datos ni eventos. Equivale a no tenerlo dado de alta |
| Ve | Solo las entidades `Kodi: ve` y `Kodi: actúa`, en lectura |
| Actúa | Además puede accionar las `Kodi: actúa` |

Así se cubre el caso de los Kodi infantiles («Ve» y, si se quiere, solo con su panel) sin depender de instalar o no
el addon.

**4.1 (controlar por instalación): descartada como control.** Instalar el addon no da acceso: un Kodi solo recibe algo
si HA lo tiene dado de alta. Sí se puede no instalarlo donde no se quiera, pero eso es una comodidad, no seguridad.

## 5. Paneles: dónde se definen (4.2.1 frente a 4.2.2)

El propietario prefiere 4.2.1 (paneles configurados en Kodi), con la condición de valorar complejidad y mantenimiento.

| Criterio | 4.2.1 Definidos en Kodi | 4.2.2 Definidos en HA | Híbrido: se editan en Kodi y se guardan en HA |
|---|---|---|---|
| Editor | Diálogos de Kodi con el mando: elegir de una lista, ordenar con subir/bajar, renombrar | Subentrada «Panel» con el selector nativo de entidades de HA (filtrado por etiqueta), desde el móvil o el PC | Diálogos de Kodi |
| Código a escribir y mantener | Alto: editor completo en Kodi, en Python 2.7 y 3 | Bajo: unas pantallas de configuración y el envío | El más alto: editor en Kodi y almacenamiento y reparto en HA |
| Compartir entre Kodi | No, salvo que se sincronice aparte | Sí: un panel se asigna a uno o a varios Kodi | Sí |
| Si se reinstala o se rompe la SD de un Kodi | Se pierde | No se pierde nada (va en la copia de HA) | No se pierde |
| Paneles distintos por Kodi | Sí | Sí: cada Kodi elige sus paneles | Sí |
| Encaje con la regla «configurable desde la UI de HA» | No aplica | Total | Parcial |
| Qué tiene de único | Editar desde el sofá | Lo más simple y robusto | Editar desde el sofá sin perder nada |

**Valoración.** Lo que el propietario busca en 4.2.1 (paneles distintos que comparten las entidades accesibles) también
lo da 4.2.2: los paneles se definen una vez, cada Kodi elige los suyos y las entidades disponibles siempre las limitan
las etiquetas y el nivel del Kodi. Lo que solo da 4.2.1 es editar desde el propio Kodi, y es lo que más cuesta: un
editor con el mando en dos versiones de Python.

**Propuesta por fases:**
1. **Fase 1, sin paneles:** el listado agrupa por áreas todo lo que el Kodi puede ver.
2. **Fase 4, paneles en HA (4.2.2)**, asignados a uno o varios Kodi.
3. **Fase 5, «edición rápida» desde Kodi** (elegida, D6): añadir o quitar una entidad de un panel desde el listado
   (menú contextual) y guardar el cambio en HA. Da lo esencial de 4.2.1 sin un editor completo y sin perder la
   configuración compartida.

## 6. Configuración compartida (punto 1 del propietario)

**Está justificada:** son varios Kodi, alguno con SD que se desgasta. Reconfigurar cada uno a mano, y otra vez tras cada
reinstalación, es justo la configuración ad hoc que se quiere evitar.

**Propuesta: HA es la única fuente de configuración.** Los ajustes del addon que hoy serían locales (qué notificaciones
mostrar, con qué eventos pausar, panel inicial) se guardan en la subentrada de cada Kodi y se envían al conectar:
- En el Kodi, el addon solo necesita estar instalado y activado. Cuando HA lo da de alta, recibe su configuración.
- Si se cambia un ajuste desde el Kodi, el addon lo envía a HA, que lo guarda. Así cumple el punto 4 del §1
  («configurable en cada Kodi») sin que la configuración viva solo en ese equipo.
- **Valores de grupo:** la entrada principal tiene los valores por defecto y cada Kodi puede cambiar algunos.
- Sin conexión con HA, el addon usa la última copia que recibió.

No se usa `kodi-addon-nextcloud` para esto: sincroniza bibliotecas y ajustes de Kodi, pero aquí HA ya tiene canal con
cada Kodi y añadir un segundo camino no se justifica.

## 7. Qué se expone y cómo se pinta

Etiquetas `Kodi: ve` y `Kodi: actúa` (D2). El componente sale del dominio:

| Dominio | Componente en Kodi |
|---|---|
| `binary_sensor` | Indicador con icono y color |
| `sensor` | Valor con unidad |
| `light`, `switch`, `fan`, `input_boolean` | Interruptor |
| `automation` | Interruptor (activar o desactivar) |
| `scene`, `script`, `button` | Botón |
| `cover` | Abrir, parar y cerrar (solo si se etiqueta a propósito) |

Pintado:
1. **K1, listado de plugin**, primero (D3).
2. **K2, ventana propia (WindowXML)** cuando haya paneles.
3. **K3, superposición sobre el vídeo**, solo para eventos si hace falta.

### 7.1 Lenguaje visual (aprobado el 26/11)

Maquetas en [maquetas_k2/](maquetas_k2/) (tablero D, «Lenguaje visual»). La primera versión (texto de estado en color,
contadores «1 alerta · 2 activos») se descartó: la organización valía, la estética no. Reglas:

- **El estado lo dice el icono, no el texto.** Activo: bloque ámbar macizo con halo e icono relleno. Reposo: gris con
  icono de contorno. Alerta: rojo con anillo que late. No disponible: apagado, borde fino y marca de sin conexión.
  Escena o botón: azul de contorno.
- El icono **cambia de forma** además de color (bombilla, puerta, ventana, presencia, ventilador, tele: variantes MDI
  de contorno y rellena), para no depender solo del color.
- El texto del estado va siempre en **gris neutro** y solo confirma.
- **Valores:** aro de 270° con escala de color (temperatura frío→confort→calor; humedad; consumo; batería) y el número
  grande en blanco.
- **Indicadores de área:** miniaturas de los iconos de lo encendido o abierto, punto rojo con icono si hay alerta,
  termómetro coloreado con la temperatura y un check tenue si todo está en reposo. Nada de contadores en texto.
- Áreas con su icono (el `icon` del registro de áreas de HA) y teclas del mando como iconos.
- En Kodi: iconos MDI blancos teñidos con `colordiffuse`, halos y aros como PNG precalculados (un aro por tramo de
  valor), latido con una animación de la ventana. Sin dependencias de terceros.

Disposición elegida el 26/11: **A (tablero por áreas) y C (filas por estancia) como vistas de pantalla completa a
elegir en la configuración, y B (panel lateral) durante la reproducción.**

**Hecho en 0.2.0 (26/11), en solo lectura:** las tres ventanas (`ventana.py` y `resources/skins/Default/1080i/`), con
el modelo en `tablero.py`. Cada Kodi elige en HA su pantalla (tablero, filas o listado) y la tecla del mando que abre
B (roja, verde, amarilla, azul o ninguna); el servicio escribe el mapa de teclas. B pausa el vídeo al abrirse y lo
reanuda al cerrarse si lo pausó él, y enseña «Ahora mismo» y el área del propio Kodi. Hasta que haya paneles (fase 4),
A y C enseñan las áreas y B el área del Kodi. Probado en un Kodi 21 de escritorio en pantalla virtual con datos de
ejemplo: pintado, navegación, cambio en vivo sin perder el foco, tecla y pausa.

Validado en una tele real el 26/11. Pendiente: llevar al listado (K1) lo que un listado permita (variantes de icono por estado).

### 7.2 Sección «Casa» en la pantalla de inicio (0.2.1)

En un clon de Estuary (el de `kodi_content_adviser`, Estuary Adviser) la casa entra en el **menú principal**, delante
de «Tiempo», solo si HA Link está activo. Con el foco en «Casa», a la derecha, tres filas de baldosas de K2:

| Fila | Qué enseña | Al pulsar |
|---|---|---|
| Ahora mismo | Lo encendido o en alerta de toda la casa, alertas primero; «Todo en reposo» si no hay nada | Aviso «solo lectura» |
| Aquí (nombre del área) | Las entidades del área de este Kodi; no sale si no tiene área o no hay nada en ella | Aviso «solo lectura» |
| Estancias | Una baldosa por área: su icono en un bloque del color de lo peor que tenga y la temperatura | El tablero en ese área |

Pulsar «Casa» abre la pantalla elegida en HA para ese Kodi.

Un termostato cuenta como «encendido» solo si está calentando o enfriando (`hvac_action`), no por estar en modo
calor: si no, todos los de una casa con calefacción llenan «Ahora mismo» en invierno (0.2.1 de la integración). Si el
termostato no informa de `hvac_action`, manda el modo.

- **Contenido:** `plugin://service.ha_link/?fila=ahora|aqui|estancias` (`inicio.py`, sin `xbmc`). Cada elemento
  lleva las propiedades de las baldosas de K2, y el skin las pinta con la misma baldosa.
- **Recarga:** Kodi solo vuelve a pedir una fila cuando cambia su dirección. El servicio deja en la ventana Home una
  revisión por fila (`ha_link.rev_<fila>`) que solo cambia si cambia lo que la fila enseña, y el skin la mete en la
  dirección. Así la potencia de las placas, que se mueve cada pocos segundos, no hace parpadear la pantalla.
- **Una lista oculta no se recarga:** las filas no se ocultan por estar vacías (como hace Estuary con las suyas). La
  fila «Aquí» se oculta con una propiedad (`ha_link.aqui`, vacía si no hay nada que enseñar).
- **La baldosa sale de este repo:** `herramientas/generar_ventanas.py` escribe `estuary/include_ha_link_inicio.xml`
  (el include `HaLinkFila`), y el parche de Estuary Adviser lo copia tal cual. Se cambia aquí y se vuelve a copiar.

Probado en el Kodi de escritorio con los datos reales del piloto (26/11): las tres filas, la navegación con el mando,
la recarga cuando llegan los datos tarde y abrir el tablero en un área.

## 8. Canal de notificaciones y eventos (D4)

Hay dos piezas, las dos de la integración y usables desde el editor visual de automatismos:

1. **Entidades `notify`**, una por Kodi más una de grupo. Usan la acción estándar `notify.send_message` (mensaje y
   título). Es lo ortodoxo en HA y sirve para los avisos sencillos.
2. **Acción `<dominio>.evento`**, para lo que necesita más que un texto:
   - Campos: tipo (`timbre`, `puerta`, `alarma`...), gravedad (info, aviso, grave), título, mensaje, imagen opcional
     (instantánea de la cámara) y duración.
   - Cada Kodi decide qué hacer según su configuración (§6): ignorarlo, notificar, pausar la reproducción o encender la
     tele por CEC (con `kodi-addon-cec`).

**Sustitución de lo actual:** el canal reemplaza a los envíos directos por JSON-RPC desde HA (`rest_command` o
`kodi.call_method` con `GUI.ShowNotification`). La migración concreta de cada instalación se documenta con esa
instalación.

**Hecho en 0.3.0 (26/11):**

- Integración: una entidad `notify` por Kodi («Avisos») y otra para todos («Avisos a todos los Kodi»), y la acción
  `kodi_link.evento` («Mandar un aviso») sobre esas entidades, con título, mensaje, tipo, gravedad y duración. En la
  subentrada de cada Kodi se elige qué hace con cada gravedad: nada, tarjeta o tarjeta y pausa (por defecto: tarjeta,
  tarjeta, y tarjeta y pausa para lo grave).
- Addon: tarjeta arriba a la derecha (abajo van los subtítulos), con el icono del tipo en un bloque del color de la
  gravedad. Probado en el Kodi de escritorio: **no se queda con el mando** (una tecla cierra la tarjeta y además hace
  lo suyo: avanzar, pausar…), lo grave pausa y se queda hasta OK o Atrás, y **no quita el salvapantallas** (en las
  casas con `cec_wake_screensaver`, quitarlo encendería la tele).
- Pendiente: la foto de la cámara en el aviso, encender la tele por CEC para lo grave, y que el addon acuse cada
  aviso para saber en HA que se ha visto.

## 9. Nombre y código compartido

- **Nombre** (D7): `kodi-addon-ha-link`, con la integración `kodi_link`. Es el canal entre HA y Kodi (panel,
  notificaciones y eventos), no solo un panel.
- **Código compartido con `kodi_parental`.** Las dos integraciones hablan con Kodi por el mismo canal. Para no
  duplicarlo (y no tener dos maneras de hacer lo mismo), conviene sacar el protocolo a un módulo común. En Kodi sería
  `script.module.*`, la forma estándar de compartir código entre addons; en HA, una librería interna. No es necesario
  para empezar: se valora cuando haya código.

## 10. Fases

0. ~~**Prueba de canal**~~ **hecha el 26/11**: funciona en los dos sentidos ([fase0-resultados.md](fase0-resultados.md)).
1. **Listado (K1) de solo lectura y maquetas.** En curso (26/11): integración `kodi_link` 0.1.0 y addon
   `service.ha_link` 0.1.0 escritos, con 54 pruebas (lógica de las dos mitades, alta desde la UI y un Kodi falso por
   WebSocket). Lenguaje visual de K2 aprobado el 26/11 (§7.1). **Piloto en marcha el 26/11** en un Kodi 21.2 real
   (LibreELEC): enlace conectado, foto acusada y cambios en vivo sin huecos. Falta ver el listado en pantalla.
   - Integración con las etiquetas y subentradas por Kodi con nivel. El listado agrupa por áreas y ya cuida el aspecto:
     iconos según estado, colores y el valor en la propia línea.
   - En paralelo, **maquetas de la ventana propia (K2)** para validar la estética antes de programarla (D6).
2. **Acciones:** nivel «Actúa», validación en HA y confirmación en Kodi para lo sensible.
3. **Canal de notificaciones y eventos:** entidades `notify`, la acción de eventos, configuración compartida (§6) y
   migración de lo actual. **Hecho en 0.3.0** (§8).
4. **Paneles en HA (4.2.2)** y la ventana propia (K2) según las maquetas aprobadas.
5. **Edición rápida desde Kodi** (D6): desde el listado o el panel, añadir, quitar o mover una entidad, guardando el
   cambio en HA.

## 11. Preguntas abiertas

Ninguna que bloquee la fase 1. K2: lenguaje visual y disposición aprobados (§7.1).
