---
title: Estadísticas, VACUUM y optimización automática en Amazon Redshift
category: maintenance
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Estadísticas, VACUUM y optimización automática

## 1. Automatización primero

Redshift incorpora automatic analyze, automatic vacuum sort, automatic vacuum delete y Automatic Table Optimization. Estas funciones reducen el mantenimiento manual y se ejecutan en segundo plano. La intervención manual debe responder a evidencia concreta, especialmente en sistemas con tráfico sostenido donde las tareas automáticas pueden no completar a tiempo.

## 2. ANALYZE

El optimizador usa estadísticas para estimar cardinalidad y elegir orden y método de join. Estadísticas ausentes o desactualizadas pueden producir malos planes.

Redshift ejecuta análisis automático y `COPY` puede analizar una tabla vacía después de cargarla. Un análisis manual puede ser útil después de cambios grandes o cuando una alerta demuestra estadísticas faltantes:

```sql
ANALYZE schema_name.table_name;
```

Buenas prácticas:

- ejecutar sobre las tablas afectadas, no asumir que toda la base lo necesita;
- priorizar columnas usadas en filtros y joins cuando corresponda;
- comprobar el plan antes y después;
- coordinar con ventanas de carga.

## 3. VACUUM

`VACUUM` puede reordenar filas y recuperar espacio de filas eliminadas. Redshift ya realiza ordenamiento y eliminación automáticos en segundo plano, por lo cual ejecutar `VACUUM` por calendario sin observar el estado puede consumir recursos innecesariamente.

Variantes disponibles incluyen `FULL`, `SORT ONLY`, `DELETE ONLY`, `REINDEX` y `RECLUSTER`, con compatibilidad y finalidad específicas. Por defecto, la fase de ordenamiento puede omitirse cuando una tabla ya está ordenada en más del umbral definido por el servicio.

Riesgos operativos:

- DML concurrente y `VACUUM` pueden ralentizarse mutuamente;
- `VACUUM DELETE` puede bloquear temporalmente actualizaciones y eliminaciones;
- se necesitan privilegios adecuados;
- el comportamiento difiere del `VACUUM` de PostgreSQL.

Por estos motivos, el agente no debe ejecutar `VACUUM` automáticamente.

## 4. Automatic Table Optimization

Con distribución y sort keys en modo `AUTO`, Redshift observa el workload y puede elegir:

- estilo o clave de distribución;
- sort key;
- compresión apropiada.

Si se definen claves manuales, esas dimensiones dejan de ser administradas automáticamente. Una clave manual solo se justifica con un patrón estable, mediciones representativas y evidencia de que la decisión automática no satisface el objetivo.

## 5. Indicadores que justifican investigar

- alerta de estadísticas faltantes;
- estimación de filas muy diferente del resultado real;
- crecimiento del área no ordenada;
- scans que dejan de aprovechar zone maps;
- ghost rows después de grandes `DELETE`;
- degradación posterior a una carga masiva;
- recomendación observable de Automatic Table Optimization pendiente o reciente.

## 6. Runbook posterior a carga masiva

1. Confirmar que la carga terminó y fue validada.
2. Medir cuánto cambió la tabla.
3. Revisar estadísticas y alertas.
4. Dar oportunidad al mantenimiento automático cuando el SLA lo permita.
5. Ejecutar `ANALYZE` manual solo si hay evidencia o necesidad inmediata.
6. Evaluar `VACUUM` solo si el desorden o ghost rows afectan consultas.
7. Comparar consultas representativas.
8. Registrar duración e impacto del mantenimiento.

## 7. Fuentes oficiales

- [Optimización automática de base de datos](https://docs.aws.amazon.com/redshift/latest/dg/c_autonomics.html)
- [Análisis de tablas](https://docs.aws.amazon.com/redshift/latest/dg/t_Analyzing_tables.html)
- [Comando VACUUM](https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html)
- [Monitoreo de Automatic Table Optimization](https://docs.aws.amazon.com/redshift/latest/dg/c_ato-enabling-disabling-monitoring.html)


