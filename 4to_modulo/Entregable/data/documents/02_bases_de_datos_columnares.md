# Bases de datos columnares

## 1. Concepto general

Una base de datos tradicional orientada a filas almacena los valores de
un registro de manera conjunta.

Por ejemplo:

  id   nombre   país   ventas
  ---- -------- ------ --------
  1    Ana      AR     100
  2    Luis     AR     200

Conceptualmente, el almacenamiento por filas puede representarse como:

``` text
[1, Ana, AR, 100]
[2, Luis, AR, 200]
```

En una base de datos columnar, los valores se almacenan agrupados por
columna:

``` text
id:      [1, 2]
nombre:  [Ana, Luis]
país:     [AR, AR]
ventas:  [100, 200]
```

------------------------------------------------------------------------

## 2. ¿Por qué es eficiente para analítica?

Las consultas analíticas suelen acceder a pocas columnas pero a muchas
filas.

Por ejemplo:

``` sql
SELECT
    country,
    SUM(amount)
FROM fact_sales
GROUP BY country;
```

Esta consulta no necesita leer:

-   Nombre del cliente.
-   Dirección.
-   Teléfono.
-   Descripción del producto.

Solo necesita:

-   `country`
-   `amount`

Una base de datos columnar puede leer únicamente esas columnas.

Esto reduce:

-   I/O.
-   Datos transferidos desde almacenamiento.
-   Memoria utilizada.
-   Tiempo de procesamiento.

------------------------------------------------------------------------

## 3. Compresión

Las columnas suelen contener valores con patrones repetitivos.

Por ejemplo:

``` text
AR
AR
AR
AR
AR
BR
BR
BR
```

Este tipo de información puede comprimirse eficientemente.

Los algoritmos de compresión pueden aprovechar:

-   Valores repetidos.
-   Secuencias ordenadas.
-   Rangos numéricos.
-   Baja cardinalidad.

Por eso, la compresión columnar suele ser particularmente eficiente para
tablas analíticas.

------------------------------------------------------------------------

## 4. Comparación con almacenamiento por filas

### Row-oriented

Ideal para:

-   OLTP.
-   Inserciones individuales.
-   Actualizaciones frecuentes.
-   Lecturas completas de registros.

Ejemplo:

``` sql
SELECT *
FROM customers
WHERE customer_id = 10;
```

### Column-oriented

Ideal para:

-   OLAP.
-   Agregaciones.
-   Reporting.
-   Data warehouses.
-   Consultas históricas.

Ejemplo:

``` sql
SELECT
    year,
    SUM(revenue)
FROM sales
GROUP BY year;
```

------------------------------------------------------------------------

## 5. Ventajas

Las bases de datos columnares ofrecen:

### Menor I/O

Solo se leen las columnas necesarias.

### Mejor compresión

Los valores de una misma columna suelen compartir características
similares.

### Procesamiento vectorizado

Las operaciones pueden ejecutarse sobre bloques de valores en lugar de
procesar un registro individual a la vez.

### Mejor rendimiento analítico

Las agregaciones y escaneos masivos suelen beneficiarse de este modelo.

------------------------------------------------------------------------

## 6. Limitaciones

No son ideales para todos los escenarios.

Pueden ser menos adecuadas para:

-   Muchas actualizaciones individuales.
-   Transacciones pequeñas y frecuentes.
-   Lecturas de registros completos.
-   Aplicaciones con baja latencia transaccional.

Por ejemplo, un sistema bancario operativo puede requerir un modelo
orientado a filas, mientras que un data warehouse corporativo puede
beneficiarse de un modelo columnar.

------------------------------------------------------------------------

## 7. Columnar storage y Data Warehousing

En un data warehouse, las tablas de hechos pueden contener millones o
miles de millones de registros.

Ejemplo:

``` text
Fact_Sales
-----------
date_key
product_key
customer_key
country_key
quantity
amount
```

Una consulta de ventas puede necesitar únicamente:

``` sql
SELECT
    country_key,
    SUM(amount)
FROM fact_sales
GROUP BY country_key;
```

El almacenamiento columnar permite evitar leer columnas irrelevantes.

------------------------------------------------------------------------

## 8. Conclusión

El almacenamiento columnar es una de las tecnologías fundamentales
detrás de los sistemas analíticos modernos.

Su eficiencia se basa principalmente en:

-   Leer únicamente las columnas necesarias.
-   Comprimir datos similares.
-   Procesar grandes bloques de datos.
-   Ejecutar operaciones en paralelo.
-   Optimizar agregaciones masivas.

Por estos motivos, es especialmente utilizado en data warehouses y
plataformas de analítica.
