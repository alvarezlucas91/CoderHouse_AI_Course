---
title: Interpretación de EXPLAIN y redistribución de datos en Amazon Redshift
category: performance
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Interpretación de EXPLAIN y redistribución de datos

## 1. Qué muestra EXPLAIN

`EXPLAIN` presenta el plan lógico elegido por el optimizador sin ejecutar la consulta. Permite observar orden de joins, métodos de join, scans, agregaciones, ordenamientos y movimiento de datos. El costo es una estimación relativa: sirve para comparar planes de una misma consulta, no como tiempo en segundos.

```sql
EXPLAIN
SELECT f.customer_id, SUM(f.amount)
FROM fact_sales f
JOIN dim_customer d ON d.customer_id = f.customer_id
WHERE f.sale_date >= dateadd(day, -30, current_date)
GROUP BY 1;
```

El plan estimado debe contrastarse con métricas reales de `SYS_QUERY_DETAIL`. Estadísticas desactualizadas pueden producir estimaciones y decisiones incorrectas.

## 2. Operadores frecuentes

- `Seq Scan`: lectura de una tabla. No es automáticamente un problema en un motor columnar.
- `Hash Join`: crea una tabla hash; puede ser apropiado, pero consume memoria.
- `Merge Join`: puede ser eficiente cuando las tablas están distribuidas y ordenadas de manera compatible.
- `Nested Loop`: suele ser costoso para grandes volúmenes y puede indicar un cross join o condición poco adecuada.
- `Aggregate`, `Sort` y `Window`: observar cardinalidad, memoria y derrames.

## 3. Etiquetas de redistribución

La red suele ser una de las operaciones más caras. Las etiquetas `DS_*` explican cómo se mueven las filas durante un join:

- `DS_DIST_NONE`: las filas ya están colocadas en los slices correspondientes; no hay redistribución.
- `DS_DIST_ALL_NONE`: la tabla interna usa `DISTSTYLE ALL`; no requiere redistribución.
- `DS_DIST_INNER`: se redistribuye la tabla interna.
- `DS_DIST_OUTER`: se redistribuye la tabla externa.
- `DS_BCAST_INNER`: se transmite una copia completa de la tabla interna a todos los nodos.
- `DS_DIST_BOTH`: se redistribuyen ambas tablas.
- `DS_DIST_ALL_INNER`: el join puede quedar concentrado en un solo slice por el uso inadecuado de `DISTSTYLE ALL` en la tabla externa.
- `DS_DIST_ERR`: falta un estilo de distribución válido.

`DS_DIST_NONE` y `DS_DIST_ALL_NONE` son generalmente favorables. `DS_BCAST_INNER` y `DS_DIST_BOTH` requieren atención cuando mueven grandes volúmenes. La etiqueta por sí sola no basta: un broadcast de una dimensión diminuta puede ser aceptable.

## 4. Diagnóstico de un join costoso

1. Identificar el join con mayor costo estimado.
2. Anotar las tablas interna y externa.
3. Revisar cardinalidad real y tamaño de ambas tablas.
4. Comprobar si la condición usa las claves de distribución.
5. Revisar skew en `SYS_QUERY_DETAIL`.
6. Verificar estadísticas con `ANALYZE`.
7. Probar una alternativa en un entorno controlado.

Posibles intervenciones:

- conservar `DISTSTYLE AUTO` y permitir Automatic Table Optimization;
- usar la misma `DISTKEY` en tablas grandes que se unen frecuentemente por esa columna;
- evaluar `DISTSTYLE ALL` para una dimensión pequeña y poco actualizada;
- preagregar antes del join;
- eliminar cross joins involuntarios;
- reducir columnas y filas antes de redistribuir.

Cambiar la distribución para favorecer una consulta puede perjudicar cargas u otras consultas. Se debe medir el workload completo.

## 5. Skew

Data skew significa que algunos slices almacenan o procesan muchas más filas que otros. Como una fase paralela termina cuando finaliza el slice más lento, un único slice saturado limita al conjunto.

Señales:

- `data_skewness` o `time_skewness` altos;
- diferencias marcadas de filas o tiempo entre slices;
- una clave de baja cardinalidad;
- valores nulos o un valor dominante en la `DISTKEY`;
- crecimiento desproporcionado de una partición lógica.

No se debe recomendar una `DISTKEY` solo porque aparece en un join. También debe tener suficiente cardinalidad y distribución uniforme.

## 6. Validación de la mejora

- usar datos representativos;
- ejecutar más de una vez y separar compilación de ejecución;
- comparar tiempo, bloques leídos, bytes redistribuidos, skew y spill;
- incluir el costo de carga y mantenimiento;
- documentar cómo revertir el cambio.

## 7. Fuentes oficiales

- [Evaluación del plan de consulta](https://docs.aws.amazon.com/redshift/latest/dg/c_data_redistribution.html)
- [Distribución de datos para optimizar consultas](https://docs.aws.amazon.com/redshift/latest/dg/t_Distributing_data.html)
- [Redistribución en EXPLAIN](https://docs.aws.amazon.com/prescriptive-guidance/latest/query-lifecycle-redshift/explain-redistribution.html)
- [Mejoras de rendimiento de consultas](https://docs.aws.amazon.com/redshift/latest/dg/query-performance-improvement-opportunities.html)


