---
title: Costo, capacidad y escalamiento en Amazon Redshift
category: cost-capacity
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Costo, capacidad y escalamiento

## 1. Provisionado y Serverless

En un clúster provisionado se eligen tipo y cantidad de nodos. Los nodos RA3 separan capacidad de cómputo de Redshift Managed Storage. En Serverless, el cómputo se mide en Redshift Processing Units y escala según el workload y la configuración del workgroup.

La elección depende de estabilidad de demanda, control operativo, compromisos de capacidad y variabilidad. No existe una modalidad universalmente más barata.

## 2. Componentes del costo

Considerar por separado:

- cómputo provisionado o RPU-hours;
- Redshift Managed Storage;
- snapshots manuales y retención;
- transferencia entre regiones;
- concurrency scaling cuando supera créditos aplicables;
- Spectrum, federated queries u otras integraciones según modalidad;
- observabilidad y almacenamiento de logs;
- costo operacional de mantener el entorno.

En Serverless, almacenamiento y cómputo se facturan por separado. El consumo de cómputo se cobra cuando el workgroup procesa actividad, con condiciones y mínimos definidos por AWS. Los precios concretos dependen de región y fecha, por lo que nunca deben quedar hardcodeados en el agente.

## 3. Controles de Serverless

- **Base capacity**: capacidad base en RPU.
- **Max capacity**: techo hasta el que puede escalar el workgroup.
- **Maximum RPU-hours**: guardrail de uso/costo durante un período, no una asignación de memoria por consulta.
- **Price-performance target**: orientación entre costo y rendimiento para el escalamiento automático.

Una base mayor puede mejorar cargas intensivas, pero aumenta potencial de consumo. Reducir capacidad puede aumentar latencia. El dimensionamiento debe usar historial real.

## 4. Escalamiento provisionado

RA3 permite que almacenamiento administrado crezca de forma independiente del SSD local y ofrece diferentes tamaños de nodo. El resize puede ser elástico o clásico según origen, destino y restricciones. Antes de cambiar:

1. medir CPU, almacenamiento, cola, spill, concurrencia y crecimiento;
2. confirmar que el problema es de capacidad y no de diseño;
3. establecer línea base de SLA y costo;
4. revisar cuotas y compatibilidad del resize;
5. preparar reversión y ventana;
6. obtener aprobación.

## 5. Árbol de decisión

- cola alta y ejecución normal: optimizar WLM o evaluar concurrency scaling.
- ejecución alta por scans o redistribución: optimizar consulta y tablas antes de escalar.
- spills persistentes en consultas válidas: revisar memoria, WLM y capacidad.
- demanda intermitente e imprevisible: evaluar Serverless.
- demanda estable y predecible: comparar provisionado y compromisos/reservas.
- almacenamiento crece más rápido que cómputo: evaluar RA3 y managed storage.

## 6. Evidencia para una recomendación

Una propuesta de capacidad debe contener:

- ventana analizada y estacionalidad;
- p50/p95 de latencia y queue time;
- concurrencia y throughput;
- RPU-hours o utilización de nodos;
- almacenamiento y crecimiento;
- costos por componente;
- alternativa sin escalamiento;
- impacto esperado, riesgo y reversión.

El agente debe marcar como estimación cualquier costo que no provenga de métricas actuales y de la página de precios correspondiente.

## 7. Fuentes oficiales

- [Capacidad de Redshift Serverless](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-capacity.html)
- [Facturación de Redshift Serverless](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing.html)
- [Capacidad on-demand y límites de costo](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing-on-demand.html)
- [Clústeres provisionados y tipos de nodo](https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html)


