---
title: Seguridad, control de acceso y auditoría en Amazon Redshift
category: security
service: amazon-redshift
language: es
source_type: official-aws-documentation
last_reviewed: 2026-08-27
---

# Seguridad, control de acceso y auditoría

## 1. Capas de seguridad

La seguridad de Redshift combina controles de AWS y controles dentro de la base:

- IAM controla acciones sobre recursos AWS y roles usados por el servicio.
- VPC, security groups y endpoints controlan conectividad.
- TLS protege conexiones en tránsito.
- cifrado protege datos y snapshots en reposo.
- usuarios, roles, schemas y privilegios controlan objetos SQL.
- row-level security y dynamic data masking reducen exposición de datos.
- audit logging registra conexiones y actividad.

Un rol IAM de servicio no reemplaza a un rol de base de datos; pertenecen a fronteras diferentes.

## 2. Menor privilegio

Role-Based Access Control permite asignar permisos a roles y luego asociarlos a usuarios u otros roles. Es preferible a otorgar permisos individualmente a gran escala.

Principios:

- evitar superusuarios para aplicaciones;
- separar roles de lectura, escritura, ETL y administración;
- conceder acceso por schema y objeto;
- restringir `PUBLIC` cuando no corresponda;
- utilizar RLS para limitar filas por tenant o dominio;
- usar dynamic data masking para datos sensibles;
- revisar herencia de roles y privilegios futuros.

Los propietarios conservan capacidades especiales. Una auditoría debe considerar ownership además de `GRANT` explícitos.

## 3. Credenciales y herramientas de IA

- usar roles IAM y credenciales temporales;
- no guardar claves en el repositorio;
- no incluir secretos en prompts o trazas;
- filtrar SQL, nombres de usuarios y datos sensibles antes de exportar observabilidad;
- limitar las herramientas del agente a operaciones de solo lectura por defecto;
- separar la generación de una recomendación de su ejecución.

Toda herramienta que pueda ejecutar SQL debe aplicar allowlists, parámetros tipados, timeout, límite de filas y auditoría.

## 4. Auditoría

Redshift registra conexiones, usuarios y actividad. Los audit logs pueden enviarse a S3 o CloudWatch en clústeres provisionados. En Serverless, los logs de auditoría se envían a CloudWatch y `SYS_CONNECTION_LOG` permite consultar conexiones.

La auditoría debe responder:

- quién se conectó y desde dónde;
- qué consulta ejecutó;
- qué objeto afectó;
- si la transacción hizo commit o rollback;
- qué cambio administrativo ocurrió;
- quién aprobó una acción propuesta por el agente.

Al enviar logs a S3 se requieren permisos específicos, incluidos acceso al ACL del bucket y escritura de objetos. La política debe limitarse al bucket y prefijo requeridos.

## 5. Respuesta ante acceso sospechoso

1. preservar logs y ventana temporal;
2. identificar usuario, rol, sesión, IP y consultas;
3. determinar objetos y datos expuestos;
4. revocar o aislar credenciales comprometidas mediante el procedimiento corporativo;
5. revisar cambios de permisos;
6. rotar secretos cuando corresponda;
7. documentar la línea temporal;
8. validar que los controles vuelven a funcionar.

Las acciones de revocación, terminación de sesiones o cambio de políticas requieren aprobación humana y permisos administrativos.

## 6. Fuentes oficiales

- [Resumen de seguridad de Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/c_security-overview.html)
- [Seguridad de objetos de base de datos](https://docs.aws.amazon.com/redshift/latest/dg/r_Database_objects.html)
- [Auditoría de base de datos](https://docs.aws.amazon.com/redshift/latest/mgmt/db-auditing.html)


