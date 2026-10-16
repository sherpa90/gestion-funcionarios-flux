# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Funcionarios Docentes y Asistentes de la Educación**: Profesionales y trabajadores de instituciones educativas en Chile. Necesitan consultar oportunamente sus registros diarios de asistencia y puntualidad, justificar inconsistencias/atrasos, solicitar días administrativos con seguimiento de saldo, subir comprobantes de licencias médicas y descargar confidencialmente sus liquidaciones mensuales de sueldo desde dispositivos móviles o computadores de escritorio.
- **Directores y Equipo Directivo**: Autoridades escolares responsables de la supervisión de personal. Necesitan aprobar o rechazar solicitudes de permisos de manera informada, supervisar la cobertura del personal y monitorear la asistencia global del establecimiento.
- **Secretaría y Personal de Recursos Humanos / Administración**: Operadores del sistema encargados de la carga masiva y sincronización de registros de relojes biométricos (vía Excel/PDF), consolidación de ausentismo, gestión documental de licencias médicas y distribución de liquidaciones de sueldo.

## Product Purpose

SGPAL (Sistema de Gestión de Personal y Asistencia Laboral) centraliza y transparenta la relación laboral y el cumplimiento horario en establecimientos educacionales chilenos. Su propósito es eliminar fricciones manuales en el control de asistencia y permisos, garantizando trazabilidad, cumplimiento de normativas educacionales/laborales y acceso claro y equitativo a la información para todos los estamentos del colegio.

## Positioning

A diferencia de los sistemas ERP o de RRHH corporativos genéricos (diseñados para empresas con dinámicas industriales o de oficina estándar), SGPAL está diseñado específicamente para el contexto normativo y operativo de la educación chilena:
- Diferenciación intrínseca entre estamentos docentes y asistentes de la educación.
- Autenticación e identificación nativa con RUT chileno con dígito verificador.
- Flujos escolares de justificaciones y permisos administrativos con calendario académico y turnos por horario de aula.
- Carga flexible compatible con los reportes típicos de relojes biométricos de colegios chilenos.

## Operating Context

- **Entornos de uso**: Uso mixto. Los funcionarios interactúan frecuentemente desde smartphones (al inicio o final de la jornada escolar, o desde el hogar para trámites y consultas de liquidaciones) y computadores de salas de profesores. El personal administrativo y directivo opera desde computadores de escritorio en oficinas de secretaría y dirección.
- **Documentos y flujos clave**:
  - Planillas Excel y archivos PDF de relojes control para procesamiento masivo de marcas.
  - Comprobantes digitales de licencias médicas emitidas por COMPIN/ISAPRE.
  - Liquidaciones de remuneraciones en formato digital protegidas con acceso por usuario.
  - Decretos y solicitudes formales de días administrativos y permisos especiales.

## Capabilities and Constraints

- **Capacidades funcionales**:
  - Control de asistencia automatizado con cálculo de puntualidad, atrasos y horas trabajadas.
  - Sistema de solicitudes, balances de días y flujo de aprobación de permisos.
  - Módulo de subida y seguimiento del estado de licencias médicas y ausentismo.
  - Módulo de consulta e historial de liquidaciones de sueldo con privacidad estricta.
  - Panel administrativo con métricas, catálogos institucionales y reportes consolidados.
- **Restricciones técnicas**:
  - Backend: Django 5.0+ con Python 3.12+.
  - Base de datos: PostgreSQL 15+.
  - Frontend: Arquitectura de plantillas Django (SSR) estilizadas con Tailwind CSS y JavaScript vanilla.
  - Integraciones de documentos: WeasyPrint (PDF), OpenPyXL (Excel), PDFPlumber.
  - Despliegue en contenedores: Docker, Docker Compose, Gunicorn/Nginx.

## Brand Commitments

- **Nombre**: SGPAL (Sistema de Gestión de Personal y Asistencia Laboral).
- **Tono y personalidad**: Institucional, confiable, transparente y sobrio. La comunicación debe ser clara y formal sin resultar burocrática ni confusa para los usuarios finales.

## Evidence on Hand

- Código fuente completo y funcional en `gestion-funcionarios/`:
  - Módulos organizados en Django apps: `asistencia`, `permisos`, `licencias`, `liquidaciones`, `catalogos`, `equipos`, `admin_dashboard`, `users`.
  - Plantillas HTML de Tailwind en `gestion-funcionarios/templates/`.
  - Manual de usuario y guías operativas en `MANUAL_USUARIO.md`, `README_ASISTENCIA.md` y `CHECKLIST_SISTEMA.md`.

## Product Principles

1. **Claridad y Confianza Inmediata**: La información sensible (asistencia, atrasos, sueldos y permisos) debe presentarse sin ambigüedades, con estados claros y lenguaje inequívoco.
2. **Paridad de Experiencia Móvil y Escritorio**: Cada función del funcionario (consultar asistencia, pedir permiso, ver liquidación) debe resolverse con igual fluidez y legibilidad tanto en un teléfono móvil como en una pantalla de escritorio.
3. **Eficiencia en la Carga Administrativa**: Las tareas recurrentes de secretaría (procesar asistencia, conciliar alegaciones y aprobar permisos) deben requerir el menor número de clics y ofrecer retroalimentación instantánea de errores o discrepancias.
4. **Respeto a la Normativa y Privacidad Escolar**: Salvaguardar la privacidad de datos personales, remuneraciones y estados de salud mediante estricto aislamiento por roles y registro de auditoría.
