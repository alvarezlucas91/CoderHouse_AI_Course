# Ejercicio 1 — Phoenix y OpenInference

## Preparación

1. Crea y activa un entorno virtual con Python 3.11 o 3.12.
2. Instala las dependencias:

   ```powershell
   pip install -r 7mo_modulo/Demo_Phoenix/requirements.txt
   pip install arize-phoenix
   ```

3. Inicia Phoenix local en otra terminal:

   ```powershell
   phoenix serve
   ```

4. Copia `.env.example` a `.env`, agrega la clave del proveedor y las tarifas
   vigentes del modelo si deseas calcular costos.
5. Comprueba la colección y luego genera las trazas:

   ```powershell
   python 7mo_modulo/Demo_Phoenix/Ejercicio_1.py --smoke-test
   python 7mo_modulo/Demo_Phoenix/Ejercicio_1.py --run-suite
   ```

Abre <http://localhost:6006>, selecciona `modulo-7-multiagente` y usa el `trace_id`
del reporte para verificar cada resultado. La suite ejecuta cinco consultas y una
sexta traza fallida. Para no mezclar sesiones, elimina previamente las trazas del
proyecto desde Phoenix o usa un nombre nuevo en `PHOENIX_PROJECT_NAME`.

El reporte se escribe en `hallazgos_phoenix.md`. Publícalo en Drive, Notion o GitHub
y sustituye `PENDIENTE` por la URL compartible.
