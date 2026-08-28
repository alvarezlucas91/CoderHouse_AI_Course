---
title: Workload Management, concurrencia y prioridades en Amazon Redshift
category: workload-management
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Workload Management, concurrencia y prioridades

## 1. Problema que resuelve WLM

Workload Management controla cómo compiten por recursos cargas ETL, dashboards, análisis ad hoc y ciencia de datos. El objetivo es proteger los acuerdos de nivel de servicio y el throughput general, no lograr que cada consulta individual sea la más rápida.

## 2. Auto WLM y WLM manual

AWS recomienda Auto WLM para la mayoría de los casos. Redshift decide concurrencia y memoria, mientras el administrador define colas, rutas y prioridades. WLM manual permite controlar slots y memoria, pero exige ajuste y puede desperdiciar recursos.

Un diseño inicial razonable separa:

- ETL crítico: prioridad alta en su ventana;
- dashboards: prioridad alta o normal y baja latencia;
- análisis ad hoc: prioridad normal;
- trabajos exploratorios: prioridad baja.

Las rutas pueden basarse en roles, grupos de usuarios o `query_group`. Las propiedades exactas y el modo de configuración difieren entre clústeres provisionados y Redshift Serverless.

## 3. Diagnosticar espera en cola

Señales:

- `queue_time` representa una fracción grande del tiempo total;
- aumenta la longitud de la cola;
- hay trabajos largos delante de consultas interactivas;
- una carga periódica coincide con la degradación;
- el tiempo de ejecución permanece estable una vez iniciada la consulta.

Antes de escalar capacidad:

1. identificar la cola y el workload;
2. comprobar prioridad y regla de asignación;
3. revisar consultas monopolizadoras;
4. separar cargas incompatibles;
5. evaluar concurrency scaling para workloads elegibles.

## 4. Query Monitoring Rules

Las QMR establecen hasta tres predicados basados en métricas y una acción. Las acciones posibles incluyen registrar, mover o abortar según la configuración aplicable. WLM evalúa las métricas periódicamente; cuando coinciden varias reglas se prioriza la acción más severa.

Casos útiles:

- registrar consultas con nested loops;
- abortar consultas que exceden un umbral extremo de CPU;
- controlar scans que leen demasiados bloques;
- detectar consultas que producen demasiadas filas intermedias.

Las acciones quedan registradas en `STL_WLM_RULE_ACTION` para clústeres provisionados. Los umbrales deben derivarse de una línea base: un valor arbitrario puede cancelar cargas legítimas.

## 5. Concurrency Scaling

Cuando una cola habilitada supera su capacidad, las consultas elegibles pueden ejecutarse en un clúster de concurrency scaling. Esto ayuda con picos de concurrencia, pero no corrige una sola consulta mal diseñada.

Es apropiado cuando:

- el problema dominante es espera por concurrencia;
- las consultas son elegibles;
- la demanda tiene picos;
- se controlan uso y costo.

No es la primera solución cuando `execution_time`, skew, spill o bytes escaneados dominan el problema.

## 6. Short Query Acceleration

SQA da prioridad a consultas cortas en un espacio dedicado para evitar que queden detrás de trabajos largos. Conviene para dashboards y consultas interactivas. Su efectividad debe comprobarse con distribución de latencias, no únicamente con promedios.

## 7. Runbook de saturación

1. Confirmar aumento de `queue_time`.
2. Clasificar consultas por cola, usuario y etiqueta.
3. Encontrar trabajos largos y su legitimidad.
4. Revisar prioridades y reglas de asignación.
5. Aplicar QMR en modo de registro antes de abortar automáticamente.
6. Evaluar SQA o concurrency scaling.
7. Medir p50, p95, throughput y costo después del cambio.

Cambiar de WLM manual a automático en un clúster provisionado puede dejar el parámetro pendiente de reinicio. Por ser una acción operativa, el agente debe pedir aprobación humana.

## 8. Fuentes oficiales

- [Workload Management](https://docs.aws.amazon.com/redshift/latest/dg/cm-c-implementing-workload-management.html)
- [Reglas de monitoreo WLM](https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-query-monitoring-rules.html)
- [Concurrency Scaling](https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling.html)
- [Configuración de WLM](https://docs.aws.amazon.com/redshift/latest/mgmt/workload-mgmt-config.html)


