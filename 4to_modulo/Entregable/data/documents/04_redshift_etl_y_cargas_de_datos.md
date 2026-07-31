# Amazon Redshift: ETL, cargas de datos y estrategias de ingestión

## 1. Introducción

Un data warehouse depende de procesos confiables para incorporar
información desde diferentes fuentes.

Un flujo típico puede ser:

``` text
Sistema origen
      ↓
Extracción
      ↓
Staging
      ↓
Transformación
      ↓
Validación
      ↓
Redshift
      ↓
Reporting / BI
```

Las fuentes pueden incluir:

-   ERP.
-   CRM.
-   APIs.
-   Bases de datos relacionales.
-   Archivos CSV.
-   Data lakes.
-   Sistemas externos.

------------------------------------------------------------------------

## 2. Staging layer

Una capa de staging permite recibir los datos antes de aplicar
transformaciones definitivas.

Ejemplo:

``` text
Source System
      ↓
stg_sales
      ↓
int_sales
      ↓
fact_sales
```

La capa de staging puede conservar:

-   Datos originales.
-   Metadata de carga.
-   Fecha de procesamiento.
-   Identificador de ejecución.
-   Sistema de origen.

Ejemplo:

``` sql
CREATE TABLE stg_sales (
    source_system VARCHAR(50),
    load_date TIMESTAMP,
    order_id VARCHAR(100),
    amount DECIMAL(18, 2)
);
```

------------------------------------------------------------------------

## 3. Full load vs incremental load

### Full load

Se reemplaza o recarga toda la información.

``` text
Origen completo
      ↓
Redshift
```

Ventajas:

-   Simplicidad.
-   Menor complejidad lógica.

Desventajas:

-   Mayor volumen procesado.
-   Mayor tiempo de ejecución.
-   Mayor consumo de recursos.

------------------------------------------------------------------------

### Incremental load

Solo se procesan los cambios.

Por ejemplo:

``` sql
WHERE updated_at > :last_successful_load
```

Ventajas:

-   Menor volumen.
-   Menor tiempo de procesamiento.
-   Menor costo operativo.

Desafíos:

-   Control de cambios.
-   Registros eliminados.
-   Reprocesamiento.
-   Idempotencia.

------------------------------------------------------------------------

## 4. Idempotencia

Un proceso idempotente puede ejecutarse más de una vez sin generar datos
incorrectos.

Por ejemplo, si una carga falla después de insertar parte de los datos,
una nueva ejecución no debería duplicarlos.

Una estrategia posible es utilizar:

``` text
Batch ID
Load ID
Source System
Business Key
```

Ejemplo conceptual:

``` sql
DELETE FROM fact_sales
WHERE load_id = '2026-07-27-001';

INSERT INTO fact_sales
SELECT *
FROM stg_sales
WHERE load_id = '2026-07-27-001';
```

------------------------------------------------------------------------

## 5. COPY y cargas masivas

Las cargas masivas son generalmente más eficientes que realizar
inserciones individuales.

Un patrón común es:

``` text
Archivo
  ↓
Object Storage
  ↓
COPY
  ↓
Redshift
```

Conceptualmente:

``` sql
COPY staging_sales
FROM 's3://bucket/path/'
IAM_ROLE 'arn:aws:iam::account:role/redshift-role'
FORMAT AS PARQUET;
```

Las cargas masivas permiten aprovechar mejor el procesamiento paralelo.

------------------------------------------------------------------------

## 6. Formatos de archivos

### CSV

Ventajas:

-   Simple.
-   Fácil de inspeccionar.
-   Compatible con muchas herramientas.

Desventajas:

-   Mayor tamaño.
-   Parsing más costoso.
-   No es columnar.

### JSON

Útil para datos semiestructurados.

Desventajas:

-   Mayor volumen.
-   Procesamiento más complejo.

### Parquet

Formato columnar muy utilizado en arquitecturas de datos modernas.

Ventajas:

-   Compresión eficiente.
-   Lectura selectiva de columnas.
-   Buen rendimiento analítico.
-   Integración con data lakes.

------------------------------------------------------------------------

## 7. CDC y cargas incrementales

Change Data Capture (CDC) permite detectar modificaciones en el sistema
origen.

Los eventos pueden representar:

``` text
INSERT
UPDATE
DELETE
```

Un flujo puede ser:

``` text
Database
    ↓
CDC
    ↓
Stream / Queue
    ↓
Transformation
    ↓
Redshift
```

Esto permite reducir la necesidad de realizar cargas completas.

------------------------------------------------------------------------

## 8. Modelo de dimensiones y hechos

Un modelo típico de data warehouse utiliza:

### Fact table

Contiene eventos cuantificables.

``` text
fact_sales
-----------
date_key
product_key
customer_key
quantity
amount
```

### Dimension table

Contiene información descriptiva.

``` text
dim_product
-----------
product_key
product_name
category
brand
```

La separación permite construir consultas analíticas eficientes.

------------------------------------------------------------------------

## 9. SCD - Slowly Changing Dimensions

Las dimensiones pueden cambiar con el tiempo.

Por ejemplo:

``` text
Cliente:
2025 → Buenos Aires
2026 → Córdoba
```

Con SCD Type 2 se conserva el historial:

``` text
customer_id | city         | valid_from | valid_to   | current
1            | Buenos Aires | 2025-01-01 | 2025-12-31 | 0
1            | Córdoba      | 2026-01-01 | NULL       | 1
```

Esto permite analizar los datos utilizando el contexto histórico
correcto.

------------------------------------------------------------------------

## 10. Control de calidad

Antes de publicar datos en tablas analíticas, es recomendable validar:

-   Claves duplicadas.
-   Valores nulos.
-   Rangos inválidos.
-   Totales esperados.
-   Cantidad de registros.
-   Integridad referencial.

Ejemplo:

``` sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT order_id) AS unique_orders
FROM stg_sales;
```

Si los valores no coinciden, puede existir duplicación.

------------------------------------------------------------------------

## 11. Diseño de pipelines robustos

Un pipeline productivo debería considerar:

``` text
Extract
  ↓
Validate
  ↓
Load staging
  ↓
Transform
  ↓
Quality checks
  ↓
Publish
  ↓
Audit
```

También es importante registrar:

-   Inicio del proceso.
-   Fin del proceso.
-   Estado.
-   Cantidad de registros.
-   Error producido.
-   Identificador de ejecución.

------------------------------------------------------------------------

## 12. Conclusión

El rendimiento y la confiabilidad de Redshift dependen tanto del diseño
de las tablas como de la estrategia de ingestión.

Un pipeline eficiente debe combinar:

-   Cargas masivas.
-   Procesamiento incremental.
-   Idempotencia.
-   Validaciones.
-   Trazabilidad.
-   Formatos eficientes.
-   Separación entre staging y modelo analítico.

La combinación de un modelo columnar, procesamiento distribuido y
pipelines bien diseñados permite construir plataformas de datos
escalables y confiables.
