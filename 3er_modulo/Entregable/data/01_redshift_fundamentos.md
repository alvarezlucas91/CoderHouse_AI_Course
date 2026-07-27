# Amazon Redshift: fundamentos y arquitectura

## 1. Introducción

Amazon Redshift es un servicio de almacenamiento de datos analítico
(data warehouse) orientado a ejecutar consultas SQL sobre grandes
volúmenes de información. Está diseñado principalmente para cargas
**OLAP** (Online Analytical Processing), donde predominan las consultas
de lectura, agregaciones, joins y análisis históricos.

A diferencia de una base de datos transaccional tradicional, Redshift
está optimizado para:

-   Procesar grandes volúmenes de datos.
-   Ejecutar consultas analíticas complejas.
-   Leer grandes cantidades de registros de manera eficiente.
-   Integrarse con ecosistemas de datos y servicios cloud.
-   Escalar capacidad de cómputo según las necesidades de la carga.

------------------------------------------------------------------------

## 2. Arquitectura de un cluster

Tradicionalmente, un cluster de Redshift está compuesto por:

### Leader node

El **leader node** recibe las consultas SQL de los clientes y coordina
su ejecución.

Sus responsabilidades incluyen:

-   Analizar y optimizar las consultas.
-   Generar el plan de ejecución.
-   Coordinar los nodos de cómputo.
-   Recibir y consolidar resultados parciales.

### Compute nodes

Los **compute nodes** almacenan los datos y ejecutan la mayor parte del
procesamiento.

Cada nodo se divide internamente en slices, que permiten distribuir el
trabajo entre diferentes unidades de procesamiento.

Una consulta puede dividirse en múltiples tareas que se ejecutan en
paralelo.

------------------------------------------------------------------------

## 3. Procesamiento MPP

Redshift utiliza un enfoque de **Massively Parallel Processing (MPP)**.

La idea principal es dividir:

1.  Los datos.
2.  La carga de trabajo.
3.  Las operaciones de una consulta.

entre múltiples unidades de procesamiento.

Por ejemplo, una consulta de agregación:

``` sql
SELECT
    country,
    SUM(amount)
FROM fact_sales
GROUP BY country;
```

puede procesarse en paralelo:

1.  Cada nodo procesa su propia porción de datos.
2.  Cada nodo calcula agregaciones parciales.
3.  Los resultados parciales se combinan.
4.  Se devuelve el resultado final.

Este enfoque permite procesar grandes volúmenes de información de forma
mucho más eficiente que una arquitectura basada en un único servidor.

------------------------------------------------------------------------

## 4. Distribución de datos

La distribución de datos es uno de los aspectos más importantes del
rendimiento.

Redshift puede utilizar diferentes estrategias:

### EVEN

Los registros se distribuyen de manera uniforme entre los nodos.

Es una opción genérica cuando no existe una columna de distribución
claramente adecuada.

### KEY

Los registros se distribuyen según el valor de una columna.

Ejemplo:

``` sql
CREATE TABLE fact_sales (
    sale_id BIGINT,
    customer_id BIGINT,
    amount DECIMAL(18, 2)
)
DISTKEY(customer_id);
```

Esta estrategia puede reducir el movimiento de datos cuando las tablas
se unen utilizando la misma clave.

### ALL

Una copia completa de la tabla se almacena en cada nodo.

Es útil para tablas pequeñas de dimensiones que se consultan
frecuentemente.

------------------------------------------------------------------------

## 5. Data redistribution

Durante una consulta, Redshift puede necesitar mover datos entre nodos.

Este proceso se denomina **data redistribution**.

Puede ocurrir cuando:

-   Dos tablas tienen diferentes claves de distribución.
-   Una tabla no está distribuida de forma compatible con otra.
-   Se ejecutan joins sobre columnas que no están co-localizadas.

El movimiento de datos entre nodos puede ser costoso, por lo que el
diseño de distribución debe considerar los patrones de consulta reales.

------------------------------------------------------------------------

## 6. Workload Management

Redshift permite administrar diferentes tipos de cargas de trabajo
mediante mecanismos de gestión de recursos.

Un entorno puede tener, por ejemplo:

-   Consultas de reporting.
-   Procesos ETL.
-   Cargas masivas.
-   Consultas ad hoc.
-   Procesos de mantenimiento.

La configuración adecuada permite evitar que una consulta pesada bloquee
o degrade el rendimiento de otros procesos.

------------------------------------------------------------------------

## 7. Buenas prácticas

Algunas buenas prácticas generales son:

-   Diseñar las claves de distribución basándose en los joins más
    frecuentes.
-   Evitar utilizar `SELECT *` en consultas productivas.
-   Mantener las estadísticas actualizadas.
-   Analizar los planes de ejecución.
-   Evitar mover grandes volúmenes de datos innecesariamente.
-   Separar cargas analíticas de cargas transaccionales.
-   Utilizar formatos columnares para cargas externas cuando sea
    posible.

------------------------------------------------------------------------

## 8. Conclusión

Redshift está diseñado para resolver problemas analíticos a gran escala
mediante una arquitectura distribuida y paralela. El rendimiento final
depende no solamente del hardware disponible, sino también de decisiones
de modelado como:

-   Distribución de tablas.
-   Ordenamiento.
-   Diseño de joins.
-   Volumen de datos transferido.
-   Estrategia de carga y mantenimiento.

Una correcta arquitectura de datos es fundamental para aprovechar sus
capacidades.
