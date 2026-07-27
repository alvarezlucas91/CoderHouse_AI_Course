# Modelado de datos y optimización de rendimiento en Amazon Redshift

## 1. Introducción

El rendimiento de Redshift depende fuertemente del diseño físico de las
tablas.

Dos tablas con el mismo modelo lógico pueden tener comportamientos muy
diferentes dependiendo de:

-   Distribution style.
-   Distribution key.
-   Sort key.
-   Compresión.
-   Diseño de joins.
-   Estadísticas.
-   Volumen de datos transferido.

------------------------------------------------------------------------

## 2. Distribution style

La estrategia de distribución define cómo se reparten las filas entre
los nodos.

### DISTSTYLE EVEN

Distribuye las filas de manera uniforme.

Puede ser apropiado cuando:

-   No existe una clave de distribución clara.
-   La tabla no participa frecuentemente en joins.
-   Se busca evitar skew.

### DISTSTYLE KEY

Distribuye los datos según una columna.

Ejemplo:

``` sql
CREATE TABLE fact_orders (
    order_id BIGINT,
    customer_id BIGINT,
    order_date DATE,
    amount DECIMAL(18, 2)
)
DISTSTYLE KEY
DISTKEY(customer_id);
```

Si otra tabla utiliza la misma clave, puede reducirse la necesidad de
redistribución.

### DISTSTYLE ALL

Replica la tabla completa en cada nodo.

Es recomendable únicamente para tablas pequeñas.

Ejemplo típico:

``` text
dim_country
dim_currency
dim_status
```

------------------------------------------------------------------------

## 3. Data skew

El **data skew** ocurre cuando algunos nodos almacenan
significativamente más datos que otros.

Ejemplo:

``` text
Node 1: 25 GB
Node 2: 24 GB
Node 3: 26 GB
Node 4: 250 GB
```

El nodo más cargado puede convertirse en un cuello de botella.

Una causa común es elegir una clave con baja cardinalidad.

Ejemplo:

``` text
country = AR
country = AR
country = AR
country = AR
...
```

Si la mayoría de los registros tienen el mismo valor, la distribución
puede ser muy desbalanceada.

------------------------------------------------------------------------

## 4. Sort keys

Una sort key define el orden físico de los datos.

Ejemplo:

``` sql
CREATE TABLE fact_sales (
    sale_date DATE,
    customer_id BIGINT,
    amount DECIMAL(18, 2)
)
SORTKEY(sale_date);
```

Esto es especialmente útil para consultas que filtran por rangos:

``` sql
SELECT *
FROM fact_sales
WHERE sale_date BETWEEN '2026-01-01' AND '2026-01-31';
```

------------------------------------------------------------------------

## 5. Zone maps

Redshift puede utilizar información sobre los rangos de valores
almacenados en bloques.

Por ejemplo:

``` text
Block 1: 2026-01-01 → 2026-01-10
Block 2: 2026-01-11 → 2026-01-20
Block 3: 2026-01-21 → 2026-01-31
```

Una consulta sobre:

``` sql
WHERE sale_date = '2026-01-15'
```

puede evitar leer bloques que no contienen valores compatibles.

Este proceso reduce el volumen de datos escaneado.

------------------------------------------------------------------------

## 6. Joins y distribución

Una consulta como:

``` sql
SELECT
    f.order_id,
    c.customer_name
FROM fact_orders f
JOIN dim_customer c
    ON f.customer_id = c.customer_id;
```

puede ejecutarse eficientemente si la distribución de las tablas
favorece la co-localización de los datos.

Si los datos están en nodos diferentes, Redshift puede tener que
redistribuirlos.

En grandes tablas de hechos, esto puede tener un impacto importante.

------------------------------------------------------------------------

## 7. Compresión

La compresión reduce el espacio utilizado y el volumen de I/O.

Los tipos de datos influyen directamente en el almacenamiento.

Ejemplo:

``` sql
BIGINT
```

puede ser innecesario si los valores reales entran en un tipo más
pequeño.

Sin embargo, los tipos deben seleccionarse teniendo en cuenta:

-   Rango de valores.
-   Precisión.
-   Compatibilidad con el modelo.
-   Necesidades futuras.

Para importes monetarios, normalmente es preferible utilizar:

``` sql
DECIMAL(18, 2)
```

en lugar de tipos flotantes cuando se requiere precisión exacta.

------------------------------------------------------------------------

## 8. Estadísticas

El optimizador necesita estadísticas actualizadas para estimar:

-   Cantidad de filas.
-   Distribución de valores.
-   Selectividad de filtros.
-   Costos de joins.

La falta de estadísticas puede provocar planes de ejecución subóptimos.

------------------------------------------------------------------------

## 9. Diagnóstico de consultas

Para optimizar una consulta es importante analizar:

-   Tiempo total.
-   Tiempo de lectura.
-   Tiempo de redistribución.
-   Tamaño de los datos procesados.
-   Orden de ejecución de los joins.

Ejemplo de consulta a analizar:

``` sql
EXPLAIN
SELECT
    c.country,
    SUM(f.amount)
FROM fact_sales f
JOIN dim_customer c
    ON f.customer_id = c.customer_id
GROUP BY c.country;
```

El plan de ejecución permite identificar posibles operaciones costosas.

------------------------------------------------------------------------

## 10. Buenas prácticas

-   Elegir distribution keys basándose en patrones de joins.
-   Evitar claves con distribución muy sesgada.
-   Utilizar sort keys para filtros frecuentes.
-   Mantener estadísticas actualizadas.
-   Reducir el número de columnas seleccionadas.
-   Evitar joins innecesarios.
-   Analizar consultas de alto consumo.
-   Utilizar tipos de datos adecuados.

------------------------------------------------------------------------

## 11. Conclusión

Optimizar Redshift requiere analizar el comportamiento físico de los
datos.

La optimización no consiste simplemente en agregar más capacidad
computacional. En muchos casos, una mejora en:

-   Distribución.
-   Ordenamiento.
-   Compresión.
-   Diseño de consultas.

puede generar un impacto mayor que aumentar recursos.
