"""Fase 0: hace de integración de HA contra un Kodi con service.ha_link.prueba instalado.

Uso: python3 probar_canal.py <host_kodi> [--via-ha <entity_id_media_player>]

1. Se conecta al WebSocket JSON-RPC del Kodi (puerto 9090), como lo haría la integración.
2. Envía pings con JSONRPC.NotifyAll (sender 'ha_link') de distintos tamaños y espera el 'Other.pong' del addon.
3. Con --via-ha, envía además los pings con la acción kodi.call_method de HA y escucha la respuesta por el mismo
   WebSocket. Necesita HA_URL (p. ej. http://homeassistant.local:8123) y HA_TOKEN_FILE (fichero con un token).
Imprime entregas, pérdidas y tiempos de ida y vuelta.
"""
import json
import os
import statistics
import sys
import threading
import time
import urllib.request

import websocket

host = sys.argv[1]
via_ha = sys.argv[sys.argv.index('--via-ha') + 1] if '--via-ha' in sys.argv else None
ws = websocket.create_connection('ws://%s:9090/jsonrpc' % host, timeout=10)
recibidos = {}
lock = threading.Lock()


def escuchar():
    while True:
        try:
            m = json.loads(ws.recv())
        except Exception:
            return
        if m.get('method') == 'Other.pong' and m['params'].get('sender') == 'service.ha_link.prueba':
            d = m['params']['data']
            with lock:
                recibidos[d['seq']] = (time.time(), d)


threading.Thread(target=escuchar, daemon=True).start()
n = [100]


def enviar_ws(seq, relleno):
    n[0] += 1
    ws.send(json.dumps({'jsonrpc': '2.0', 'id': n[0], 'method': 'JSONRPC.NotifyAll', 'params': {
        'sender': 'ha_link', 'message': 'ping', 'data': {'seq': seq, 't': time.time(), 'origen': 'ws', 'relleno': relleno}}}))


def enviar_ha(seq, relleno):
    tok = open(os.path.expanduser(os.environ['HA_TOKEN_FILE'])).read().strip()
    cuerpo = {'entity_id': via_ha, 'method': 'JSONRPC.NotifyAll', 'sender': 'ha_link', 'message': 'ping',
              'data': {'seq': seq, 't': time.time(), 'origen': 'ha', 'relleno': relleno}}
    r = urllib.request.Request(os.environ['HA_URL'].rstrip('/') + '/api/services/kodi/call_method', json.dumps(cuerpo).encode(),
                               {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    urllib.request.urlopen(r, timeout=15).read()


def ronda(nombre, enviar, tamanos, repeticiones, base):
    for tam in tamanos:
        seqs = []
        for i in range(repeticiones):
            seq = base + tam * 100 + i
            seqs.append((seq, time.time()))
            enviar(seq, 'x' * tam)
            time.sleep(0.2)
        time.sleep(2)
        with lock:
            rtt = [(recibidos[s][0] - t0) * 1000 for s, t0 in seqs if s in recibidos]
        print('%-6s %7d bytes: %d/%d entregados, ida y vuelta mediana %s ms, máx %s ms' % (
            nombre, tam, len(rtt), repeticiones, round(statistics.median(rtt)) if rtt else '-', round(max(rtt)) if rtt else '-'))


ronda('ws', enviar_ws, [10, 1000, 10000, 60000], 5, 1000000)
if via_ha:
    ronda('ha', enviar_ha, [10, 1000, 10000], 5, 2000000)
ws.close()
