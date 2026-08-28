---
title: Bloqueos, transacciones y consultas detenidas en Amazon Redshift
category: incident-runbook
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Bloqueos, transacciones y consultas detenidas

## 1. No toda consulta que parece detenida está bloqueada

Una consulta puede parecer colgada por:

- espera en una cola WLM;
- bloqueo de otra transacción;
- consulta costosa todavía activa;
- conexión de cliente interrumpida aunque el servidor haya terminado;
- problema de red o MTU;
- commit o rollback prolongado.

El diagnóstico debe distinguir estos casos antes de cancelar sesiones.

## 2. Procedimiento de diagnóstico

1. Buscar la consulta en `SYS_QUERY_HISTORY` y revisar estado, cola y ejecución.
2. Identificar `session_id` y `transaction_id`.
3. Revisar transacciones abiertas y locks con `SVV_TRANSACTIONS` y `STV_LOCKS`, según el entorno.
4. Relacionar la transacción con `SYS_TRANSACTION_HISTORY` cuando ya finalizó.
5. Determinar quién espera, quién bloquea y desde cuándo.
6. Contactar al propietario del workload.
7. Elegir entre esperar, solicitar commit/rollback o terminar la sesión.

`SYS_TRANSACTION_HISTORY` muestra aislamiento y resultado (`committed` o `rolledback`), pero solo es visible para superusuarios.

## 3. Causas típicas

- transacción interactiva olvidada;
- `UPDATE`, `DELETE`, `ALTER TABLE` o mantenimiento concurrente;
- aplicación sin límites de tiempo ni manejo de rollback;
- pool que conserva sesiones con transacciones abiertas;
- operación DDL durante cargas;
- cliente desconectado sin que el operador haya confirmado el estado del servidor.

## 4. Principios de resolución

La primera opción es permitir que el propietario termine la transacción correctamente. Terminar un backend fuerza rollback y libera locks, pero puede perder trabajo, prolongar la recuperación y afectar usuarios.

`PG_TERMINATE_BACKEND` es una acción crítica:

```sql
SELECT pg_terminate_backend(:session_id);
```

El sistema de IA puede recomendarla solo cuando:

- identificó con evidencia la sesión bloqueadora;
- evaluó el impacto del rollback;
- confirmó que no es una operación crítica legítima;
- existe aprobación humana explícita;
- registró actor, motivo y `session_id`.

Nunca debe interpolar directamente en SQL un identificador suministrado por texto libre. Debe validarlo como entero y aplicar autorización.

## 5. Prevención

- transacciones cortas y con manejo explícito de excepciones;
- timeouts apropiados en aplicación y driver;
- pool de conexiones configurado y observado;
- separar DDL, cargas y mantenimiento en ventanas controladas;
- alertar sobre transacciones abiertas demasiado tiempo;
- etiquetar workloads para atribución;
- documentar responsables y escalamiento.

## 6. Salida esperada del agente

El diagnóstico debe diferenciar hechos e hipótesis:

```text
Hecho: la consulta Q espera y no acumula tiempo de ejecución.
Hecho: la sesión S mantiene un lock sobre la tabla T desde la hora H.
Hipótesis: una transacción sin commit bloquea el DDL.
Acción reversible: contactar al propietario y solicitar commit o rollback.
Acción crítica: terminar S; requiere aprobación humana.
```

## 7. Fuentes oficiales

- [Consultas detenidas](https://docs.aws.amazon.com/redshift/latest/dg/queries-troubleshooting-query-hangs.html)
- [SYS_TRANSACTION_HISTORY](https://docs.aws.amazon.com/redshift/latest/dg/SYS_TRANSACTION_HISTORY.html)
- [Resolución de problemas de consultas](https://docs.aws.amazon.com/redshift/latest/dg/queries-troubleshooting.html)
- [Guía para desarrolladores de Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/redshift-dg.pdf)


