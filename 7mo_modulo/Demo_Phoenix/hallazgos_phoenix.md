# Hallazgos de observabilidad — Phoenix

> Generado automáticamente. Abrir `http://localhost:6006` y filtrar el proyecto
> `modulo-7-multiagente`. Estos son los resultados de la demostración.

## Resultados

| Traza | Estado | Total ms | Chroma ms | Red/API LLM ms | Proceso ms | Tokens | Grounded |
|---|---:|---:|---:|---:|---:|---:|---:|
| `2f2602027f67b643cbef785da0a6e3c1` | OK | 3825.0 | 987.0 | 2781.7 | 0.0 | 2682 | True |
| `c0260e2a2b6acde4f2c1d68aacc247b6` | OK | 2860.3 | 277.4 | 2581.4 | 0.1 | 2927 | True |
| `d530a19fd488aa6d12ed60895c11c921` | OK | 6590.9 | 302.1 | 6287.3 | 0.0 | 3251 | False |
| `f41bf4f4cf59698040bda409206a65af` | OK | 22551.2 | 245.5 | 22304.3 | 0.1 | 3184 | True |
| `b1fe43e7ed52aece450f3d9af0d7fb93` | OK | 23990.8 | 245.6 | 23743.6 | 0.1 | 3376 | True |
| `ab46fcfd4a6ad52a6226940c3ee6d536` | ERROR | 85.7 | 0.0 | 0.0 | 0.0 | 0 | False |

## Análisis

El span dominante fue **generación del LLM/red** en la traza `b1fe43e7ed52aece450f3d9af0d7fb93`. La llamada LLM tardó 23743.6 ms (red + inferencia remota), Chroma 245.6 ms (proceso local) y el procesamiento local medido 0.1 ms. El razonamiento más largo fue `b1fe43e7ed52aece450f3d9af0d7fb93` con 3376 tokens; costo: USD 0.001168.

- **Latencia:** `app.network_latency_ms` incluye transporte e inferencia de la API;
  `app.processing_latency_ms` cubre construcción/parseo local; Chroma se marca como
  `local_processing`. El span OpenAI permite inspeccionar además la llamada del SDK.
- **Groundedness:** se exige al menos una cita válida `[n]` dentro del rango de
  documentos recuperados. `grounded=false` indica respuesta sin evidencia suficiente
  o citas inválidas y se ve también en el span de validación.

### Posible falta de groundedness

La traza `d530a19fd488aa6d12ed60895c11c921` fue marcada como
`grounded=false`. Aunque el flujo terminó correctamente, la respuesta no cumplió la
validación de citas: pudo haber omitido citas, utilizado índices fuera del rango de
documentos recuperados o indicado que no estaba completamente fundamentada. Esto es
evidencia de una respuesta potencialmente no sustentada, pero no demuestra por sí
solo una alucinación. Para confirmarla se debe comparar manualmente la respuesta del
LLM con los documentos visibles en el span `chroma.collection.query`.

- **Fallo intencional:** la fila `ERROR` usa una ruta Chroma inexistente/no válida. El
  span `tool.rag_search` y su ancestro quedan en estado ERROR, en vez de convertir el
  error en evidencia.
- **Eficiencia:** reducir `top_k`, recortar fragmentos repetidos y limitar el contexto
  enviado al analista baja tokens y latencia sin ocultar la recuperación.
