#!/bin/sh
set -eu

if [ ! -f /data/vectorstore/chroma.sqlite3 ]; then
  echo "Inicializando copia escribible del vectorstore..."
  cp -a /seed/vectorstore/. /data/vectorstore/
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
