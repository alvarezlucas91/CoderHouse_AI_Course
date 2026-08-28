---
title: Diagnóstico de COPY y errores de carga en Amazon Redshift
category: ingestion
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Diagnóstico de COPY y errores de carga

## 1. Por qué usar COPY

`COPY` aprovecha la arquitectura MPP para cargar datos en paralelo desde S3 y otras fuentes admitidas. Para grandes volúmenes es preferible a ejecutar muchos `INSERT` individuales.

Una operación `COPY` que lee múltiples archivos es atómica: si falla la operación, se revierte la transacción completa. Si se ejecuta dentro de un bloque transaccional y la sesión termina antes del commit, también se revierte.

## 2. Triage de un fallo

1. Capturar mensaje, `query_id`, tabla y hora.
2. Confirmar región, ruta y permisos de S3.
3. Consultar `SYS_LOAD_ERROR_DETAIL`.
4. Identificar archivo, línea, columna, tipo, código y mensaje.
5. Corregir el dato o el contrato de carga.
6. Validar con `NOLOAD` antes de repetir una carga costosa.

```sql
SELECT query_id,
       start_time,
       TRIM(file_name) AS file_name,
       line_number,
       TRIM(column_name) AS column_name,
       TRIM(column_type) AS column_type,
       error_code,
       TRIM(error_message) AS error_message
FROM sys_load_error_detail
WHERE query_id = :query_id
ORDER BY start_time, file_name, line_number
LIMIT 100;
```

`SYS_LOAD_ERROR_DETAIL` es preferible para cobertura unificada. `STL_LOAD_ERRORS` y `STL_LOADERROR_DETAIL` son históricos, pero `STL_LOAD_ERRORS` no incluye Serverless ni consultas ejecutadas en concurrency scaling.

## 3. Errores frecuentes

- región del bucket diferente y ausencia del parámetro `REGION`;
- rol IAM sin acceso al objeto o a la clave KMS;
- delimitador incorrecto;
- cantidad de columnas distinta del DDL;
- valor fuera del rango del tipo;
- formatos inválidos de fecha o timestamp;
- datos JSON mal formados;
- codificación incompatible o UTF-8 inválido;
- archivo inexistente;
- valores nulos para columnas `NOT NULL`.

No se debe usar `MAXERROR` o `IGNOREALLERRORS` como solución genérica: pueden ocultar degradación de calidad. Si se toleran filas defectuosas, el umbral debe estar aprobado, medido y acompañado por reconciliación.

## 4. Carga lenta

Un único archivo grande limita el paralelismo. AWS recomienda múltiples archivos de tamaño parecido; para clústeres provisionados, una guía es usar una cantidad múltiplo de slices y archivos comprimidos de aproximadamente 1 MB a 1 GB. Ejecutar varios `COPY` concurrentes hacia la misma tabla puede serializar la carga; suele convenir un solo `COPY` que lea varios archivos.

También revisar:

- compresión y formato columnar, por ejemplo Parquet;
- región y latencia;
- tamaño y cantidad de archivos;
- WLM y espera en cola;
- transformación previa innecesaria;
- estadísticas y compresión automática.

## 5. Validación segura

`NOLOAD` analiza archivos sin insertar filas:

```sql
COPY schema_name.target_table
FROM 's3://bucket/prefix/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftLoadRole'
FORMAT AS PARQUET
NOLOAD;
```

El ARN es ilustrativo y debe venir de configuración segura. Nunca deben aparecer credenciales permanentes en SQL, prompts, trazas ni repositorios.

Después de cargar:

- comparar conteos y totales de control;
- verificar duplicados e idempotencia;
- revisar errores tolerados;
- confirmar commit;
- medir duración y volumen;
- conservar un identificador de lote.

## 6. Fuentes oficiales

- [Carga con COPY](https://docs.aws.amazon.com/redshift/latest/dg/t_Loading_tables_with_the_COPY_command.html)
- [SYS_LOAD_ERROR_DETAIL](https://docs.aws.amazon.com/redshift/latest/dg/SYS_LOAD_ERROR_DETAIL.html)
- [Resolución de errores de carga](https://docs.aws.amazon.com/redshift/latest/dg/t_Troubleshooting_load_errors.html)
- [Operaciones de carga y NOLOAD](https://docs.aws.amazon.com/redshift/latest/dg/copy-parameters-data-load.html)
- [Carga demasiado lenta](https://docs.aws.amazon.com/redshift/latest/dg/queries-troubleshooting-load-takes-too-long.html)


