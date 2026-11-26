#!/usr/bin/env bash
# Empaqueta el addon de Kodi en un zip instalable («Instalar desde un archivo zip»).
# Uso: ./build_zip.sh   ->  dist/addon/service.ha_link-<versión>.zip (+ .sha256)
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDON="${RAIZ}/addon/service.ha_link"
VERSION=$(sed -n 's/.*<addon[^>]* version="\([^"]*\)".*/\1/p' "${ADDON}/addon.xml" | head -n 1)
[ -n "$VERSION" ] || { echo "ERROR: no se pudo leer la versión de addon.xml"; exit 1; }
DIST="${RAIZ}/dist/addon"
ZIP="${DIST}/service.ha_link-${VERSION}.zip"
mkdir -p "$DIST"
rm -f "$ZIP"

python3 - "$RAIZ/addon" "service.ha_link" "$ZIP" <<'PY'
import os, sys, zipfile
padre, nombre, salida = sys.argv[1:4]
excluir = ("__pycache__", ".pytest_cache")
with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for raiz, dirs, ficheros in os.walk(os.path.join(padre, nombre)):
        dirs[:] = sorted(d for d in dirs if d not in excluir and not d.startswith("."))
        for f in sorted(ficheros):
            if f.endswith((".pyc", ".pyo")) or f.startswith("."):
                continue
            ruta = os.path.join(raiz, f)
            zf.write(ruta, os.path.relpath(ruta, padre))
PY
( cd "$DIST" && sha256sum "$(basename "$ZIP")" > "$(basename "$ZIP").sha256" )
echo "OK: ${ZIP}"
