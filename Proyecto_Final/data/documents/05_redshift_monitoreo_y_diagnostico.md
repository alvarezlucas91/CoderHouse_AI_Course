---
title: Monitoreo y diagnóstico de consultas en Amazon Redshift
category: monitoring
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Monitoreo y diagnóstico de consultas en Amazon Redshift

## 1. Objetivo

Este documento presenta un método reproducible para investigar consultas lentas. La regla principal es separar el tiempo de espera en cola del tiempo de ejecución y luego analizar los pasos internos. Una consulta lenta no implica necesariamente falta de capacidad: puede estar esperando recursos, leyendo demasiados bloques, redistribuyendo datos o derramando resultados intermedios a disco.

## 2. Elegir las vistas correctas

AWS recomienda las vistas `SYS_*` para observación unificada de clústeres provisionados, concurrency scaling y Redshift Serverless.

- `SYS_QUERY_HISTORY`: una fila por consulta, en ejecución o finalizada, con tiempos acumulados, estado y texto.
- `SYS_QUERY_DETAIL`: métricas por child query, stream, segmento o paso.
- `SYS_TRANSACTION_HISTORY`: estado de commit o rollback; solo es visible para superusuarios.
- Las vistas históricas `STL_*`, `SVL_*` y `STV_*` siguen siendo útiles, pero algunas solo cubren el clúster provisionado principal.

La visibilidad depende del usuario: un superusuario puede observar todas las filas; un usuario regular normalmente ve las propias.

## 3. Triage inicial

Buscar primero las consultas recientes de mayor duración:

```sql
SELECT query_id,
       user_id,
       query_type,
       status,
       start_time,
       end_time,
       elapsed_time,
       queue_time,
       execution_time,
       TRIM(query_text) AS query_text
FROM sys_query_history
WHERE start_time >= dateadd(hour, -2, current_timestamp)
ORDER BY elapsed_time DESC
LIMIT 20;
```

Los nombres disponibles pueden variar con la versión; antes de automatizar la consulta se debe comprobar el esquema de la vista. Interpretación:

- `queue_time` alto y `execution_time` normal: investigar WLM y concurrencia.
- `execution_time` alto: inspeccionar pasos, distribución, filtros, estadísticas y memoria.
- estado fallido: correlacionar el error con la transacción y los logs de carga si corresponde.
- texto igual con tiempos muy variables: comparar volumen de entrada, cola, caché y concurrencia entre ejecuciones.

## 4. Análisis por pasos

Para un `query_id` problemático:

```sql
SELECT query_id,
       metrics_level,
       step_name,
       table_name,
       duration,
       input_rows,
       output_rows,
       blocks_read,
       local_read_io,
       remote_read_io,
       data_skewness,
       time_skewness,
       spilled_block_local_disk,
       spilled_block_remote_disk,
       alert
FROM sys_query_detail
WHERE query_id = :query_id
  AND metrics_level = 'Step'
ORDER BY duration DESC;
```

Señales importantes:

- `blocks_read` alto: el filtro puede ser poco selectivo o no aprovechar sort keys y zone maps.
- `remote_read_io` alto: hubo más lectura desde almacenamiento remoto que desde la caché local.
- `data_skewness` alto: las filas se distribuyeron de forma desigual.
- `time_skewness` alto: algunos slices tardaron mucho más que otros.
- `spilled_block_local_disk` o `spilled_block_remote_disk` mayores que cero: una operación intermedia no tuvo memoria suficiente.
- `input_rows` muy superior a `output_rows`: conviene filtrar o preagregar antes.
- `alert` no vacío: revisar la advertencia antes de cambiar capacidad.

## 5. Árbol de decisión

1. Confirmar el `query_id`, usuario, horario, estado y texto.
2. Separar cola de ejecución.
3. Si domina la cola, revisar WLM, prioridades y concurrency scaling.
4. Si domina la ejecución, obtener `EXPLAIN` y revisar `SYS_QUERY_DETAIL`.
5. Si hay skew, revisar claves de distribución y cardinalidad.
6. Si hay spill, reducir filas intermedias o revisar memoria y WLM.
7. Si hay scans excesivos, revisar predicados, sort keys y estadísticas.
8. Comparar contra una ejecución base representativa.
9. Cambiar una sola variable y volver a medir.

## 6. Evidencia mínima para el agente

Un diagnóstico confiable debe citar:

- identificador y ventana temporal;
- tiempo total, de cola y de ejecución;
- paso más costoso;
- tablas implicadas;
- bloques y filas procesados;
- skew o spill observado;
- plan `EXPLAIN` cuando se recomiende cambiar el diseño.

Sin estas señales, el sistema debe presentar hipótesis y solicitar datos, no afirmar una causa.

## 7. Fuentes oficiales

- [SYS_QUERY_HISTORY](https://docs.aws.amazon.com/redshift/latest/dg/SYS_QUERY_HISTORY.html)
- [SYS_QUERY_DETAIL](https://docs.aws.amazon.com/redshift/latest/dg/SYS_QUERY_DETAIL.html)
- [Mejoras de rendimiento de consultas](https://docs.aws.amazon.com/redshift/latest/dg/query-performance-improvement-opportunities.html)
- [Resolución de problemas de consultas](https://docs.aws.amazon.com/redshift/latest/dg/queries-troubleshooting.html)


