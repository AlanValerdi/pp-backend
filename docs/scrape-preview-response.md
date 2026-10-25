# Actual scrape preview response

Captured on 2026-10-11T06:31:38.349329+00:00 from `http://localhost:8001/api/v1/scrape/preview`.

Request: authenticated `POST`. HTTP response: **200 OK**. Authentication credentials are omitted.

## Summary

- Status: **succeeded**; stop reason: `detail_limit`.
- Requests: **12** (one careers page, one listing, ten detail pages).
- Detail attempts: **10**; successful parses: **10**; failures: **0**.
- Duration: **13.648 seconds**.
- No catalog or scrape-run records were written by this preview.
- All ten parsed program numbers match the corresponding listing folios.
- Preview log trace: `preview-e2ee718d7fa7425f91d00265f3bbbe3f`.

## Returned offers

These are the first discovered samples, not a representative sample of every career.

| Folio | Program | Company | Type | Start | End | Area IDs |
| --- | --- | --- | --- | --- | --- | --- |
| 246834 | PROGRAMA PARA ALUMNOS EXENTOS DE SERVICIO SOCIAL | DIRECCION DE SERVICIO SOCIAL | servicio_social | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 246965 | PRACTICANTE DE COMPRAS | J.V. ABASTECEDORA DE MONTACARGAS, S.A. DE C.V. | practica_profesional | 2027-01-05 | 2027-04-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 246971 | PRACTICANTE DE VENTAS | J.V. ABASTECEDORA DE MONTACARGAS, S.A. DE C.V. | practica_profesional | 2027-01-05 | 2027-05-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 247036 | CANTAR BIEN, PARA VIVIR MEJOR | COMPLEJO CULTURAL UNIVERSITARIO | servicio_social | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 247118 | AUXILIAR DE PROCESOS Y CALIDAD | IT SOLUTIONS GLOBAL INCORPORATED S. DE R.L. | practica_profesional | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 247123 | GESTIÓN DE CONTRATOS, CONVENIOS Y OBLIGACIONES LEGALES EN UNA EMPRESA TURÍSTICA. | SUSANA KARENINA AGUILAR HERNÁNDEZ | practica_profesional | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 247142 | APOYO EN EL DESARROLLO DE HERRAMIENTAS COMPUTACIONALES PARA LA FORMACIÓN ACTUARIAL | FACULTAD DE CS.FISICO MATEMATICAS | servicio_social | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 247143 | PROGRAMA DE EXPERIENCIA PROFESIONAL APLICADA | FACULTAD DE CS.FISICO MATEMATICAS | practica_profesional | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 247146 | PROGRAMA DE MEJORA DEL PROCESO DE ENSEÑANZA-APRENDIZAJE DE LA UNIVERSIDAD | FACULTAD DE CS.FISICO MATEMATICAS | servicio_social | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |
| 247162 | GESTIÓN, ANÁLISIS Y ADMINISTRACIÓN DE SEGUROS Y FIANZAS | SEGFIANZ CONSULTORES, AGENTE DE SEGUROS Y DE FIANZAS, S.A. DE C.V., | practica_profesional | 2027-01-05 | 2027-07-05 | 25d628fe-d316-59e0-846d-2518bb2250f3 |

## Per-request diagnostics

| # | Stage | HTTP | Duration (seconds) | Error |
| --- | --- | --- | --- | --- |
| 1 | careers | 200 | 2.305 | — |
| 2 | listing | 200 | 1.799 | — |
| 3 | detail | 200 | 0.519 | — |
| 4 | detail | 200 | 0.469 | — |
| 5 | detail | 200 | 0.526 | — |
| 6 | detail | 200 | 0.519 | — |
| 7 | detail | 200 | 0.512 | — |
| 8 | detail | 200 | 0.536 | — |
| 9 | detail | 200 | 0.517 | — |
| 10 | detail | 200 | 0.473 | — |
| 11 | detail | 200 | 0.515 | — |
| 12 | detail | 200 | 0.516 | — |

## Rebuild and interrupted run

The API image was rebuilt and the API container recreated on port 8001. Startup migrations
completed and `/health` returned `{"status":"ok"}`. PostgreSQL and the other project’s
MySQL/API containers remained running.

Run 1 was recorded as `failed`, with `finishedAt` equal to `2026-10-11T06:26:43.084451Z`
and error `Scrape cancelled during shutdown`. No new full scrape was started.

## Complete JSON response

This is the actual endpoint response, including full normalized offer fields and request parameters.

```json
{
  "status": "succeeded",
  "requestCount": 12,
  "detailAttempts": 10,
  "successfulParses": 10,
  "failures": 0,
  "durationSeconds": 13.648,
  "stopReason": "detail_limit",
  "offers": [
    {
      "uuid": "5d135e01-35a7-5b68-97d4-04fdfd7c17e7",
      "listing": {
        "folio": "246834",
        "programa": "PROGRAMA PARA ALUMNOS EXENTOS DE SERVICIO SOCIAL",
        "tipo": "servicio_social",
        "area": "SÓLO PARA TRABAJADORES DE LA FEDERACIÓN, MAYORES DE 60 AÑOS, ENTRE OTROS QUE ESTAN EN LA PÁG WEB.",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "DIRECCION DE SERVICIO SOCIAL"
      },
      "summary": {
        "tipo": "servicio_social",
        "programNumber": "246834",
        "registeredAt": "2026-09-01",
        "registeredAtRaw": "01/09/26",
        "company": "DIRECCION DE SERVICIO SOCIAL",
        "sector": "UNIVERSITARIO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "PROGRAMA PARA ALUMNOS EXENTOS DE SERVICIO SOCIAL",
        "programType": "MULTIDISCIPLINARIO",
        "department": "SÓLO PARA TRABAJADORES DE LA FEDERACIÓN, MAYORES DE 60 AÑOS, ENTRE OTROS QUE ESTAN EN LA PÁG WEB.",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "SIN RESPONSABLE",
        "position": "SIN PUESTO",
        "email": "servicio.social@correo.buap.mx",
        "phone": "222 2295500 EXT 2501",
        "interviewAddress": "Presentar con el coordinador de la unidad académica para verificar si aplica a este programa",
        "workAddress": "Presentar con el coordinador de la unidad académica para verificar si aplica a este programa"
      },
      "appointment": {
        "addressee": "MTRO. RICARDO VALDERRAMA VALDEZ",
        "position": "DIRECTOR DE SERVICIO SOCIAL"
      },
      "programInfo": {
        "monthlyStipend": "",
        "otherSupport": "",
        "socialAxes": [],
        "promotesEntrepreneurship": false
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "",
          "competencies": ""
        }
      ]
    },
    {
      "uuid": "b52152f7-5243-54a2-b984-3f22e24992af",
      "listing": {
        "folio": "246965",
        "programa": "PRACTICANTE DE COMPRAS",
        "tipo": "practica_profesional",
        "area": "FINANZAS",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "J.V. ABASTECEDORA DE MONTACARGAS, S.A. DE C.V."
      },
      "summary": {
        "tipo": "practica_profesional",
        "programNumber": "246965",
        "registeredAt": "2026-09-01",
        "registeredAtRaw": "01/09/26",
        "company": "J.V. ABASTECEDORA DE MONTACARGAS, S.A. DE C.V.",
        "sector": "PRIVADO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "PRACTICANTE DE COMPRAS",
        "programType": "MULTIDISCIPLINARIO",
        "department": "FINANZAS",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-04-05",
        "endDateRaw": "05/04/27",
        "durationMonths": 3
      },
      "supervisor": {
        "name": "GERARDO CUAUTLE MONTES",
        "position": "GERENTE DE RECURSOS HUMANOS",
        "email": "gerardo.c@jvmontacargas.com.mx",
        "phone": "2228134824",
        "interviewAddress": "PROLONGACIÓN VICTORIA 93, 0",
        "workAddress": "Anillo Perif. Ecológico #2, 72710 San Lorenzo Almecatla, Pue."
      },
      "appointment": {
        "addressee": "GERARDO CUAUTLE MONTES",
        "position": "GERENTE DE RECURSOS HUMANOS"
      },
      "programInfo": {
        "monthlyStipend": "$1,200.00",
        "otherSupport": "Cursos de SAP",
        "socialAxes": [
          "Empleo justo y bien remunerado",
          "Innovación"
        ],
        "promotesEntrepreneurship": true
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "1.Apoyo en la gestión de requisiciones internas: Búsqueda y comparación de proveedores.\n2. Elaboración de órdenes de compra en SAP\n3. Seguimiento de entregas: Confirmación de entregas en tiempo y forma con proveedores. Comunicación con almacén o usuarios para validar recepción de mercancía.\n4. Actualización de base de datos de proveedores: Registro y mantenimiento de contactos, condiciones de pago, líneas de productos y experiencia con cada proveedor.\n5. Archivo y control documental: Organización de cotizaciones, órdenes de compra y comprobantes de recepción. Escaneo de documentos para respaldo digital.\n6. Apoyo en control de inventarios críticos: Revisión de niveles mínimos y máximos de refacciones o insumos de uso frecuente. Notificación oportuna de materiales por reabastecer.\n7. Seguimiento a pendientes de facturación: Confirmación de entrega de facturas por parte de proveedores. Comunicación con Cuentas por Pagar para seguimiento de pagos.\n8. Apoyo general administrativo: Generación de reportes de compras. Organización de expedientes físicos y digitales.",
          "competencies": "Responsabilidad, Ética y honestidad, Compromiso, Trabajo en Equipo, enseñanza del manejo en SAP, CONTPAQi, Excel, elaboración de reportes Industriales, Integrarse rápidamente a un entorno de ritmo operativo e industrial."
        }
      ]
    },
    {
      "uuid": "8e0e9642-bf14-51f9-ae85-4a1ee0f62d77",
      "listing": {
        "folio": "246971",
        "programa": "PRACTICANTE DE VENTAS",
        "tipo": "practica_profesional",
        "area": "VENTAS",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "J.V. ABASTECEDORA DE MONTACARGAS, S.A. DE C.V."
      },
      "summary": {
        "tipo": "practica_profesional",
        "programNumber": "246971",
        "registeredAt": "2026-09-01",
        "registeredAtRaw": "01/09/26",
        "company": "J.V. ABASTECEDORA DE MONTACARGAS, S.A. DE C.V.",
        "sector": "PRIVADO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "PRACTICANTE DE VENTAS",
        "programType": "MULTIDISCIPLINARIO",
        "department": "VENTAS",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-05-05",
        "endDateRaw": "05/05/27",
        "durationMonths": 4
      },
      "supervisor": {
        "name": "GERARDO CUAUTLE MONTES",
        "position": "GERENTE DE RECURSOS HUMANOS",
        "email": "gerardo.c@jvmontacargas.com.mx",
        "phone": "2228134824",
        "interviewAddress": "Prol. Victoria 93, San Miguel, 72700 Heroica Puebla de Zaragoza, Pue.",
        "workAddress": "Anillo Perif. Ecológico #2, 72710 San Lorenzo Almecatla, Pue."
      },
      "appointment": {
        "addressee": "GERARDO CUAUTLE MONTES",
        "position": "GERENTE DE RECURSOS HUMANOS"
      },
      "programInfo": {
        "monthlyStipend": "$1,200.00",
        "otherSupport": "Cursos de SAP",
        "socialAxes": [
          "Empleo justo y bien remunerado",
          "Innovación"
        ],
        "promotesEntrepreneurship": true
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "1. Apoyo en la atención y gestión de clientes: Responder a consultas básicas de clientes sobre productos, precios y disponibilidad de montacargas a través de correo electrónico, teléfono o chat en línea.\n2. Apoyo en la presentación y demostración de productos: Demostraciones de producto, Acompañar al equipo de ventas o ser parte de demostraciones de montacargas para clientes potenciales, destacando las características, ventajas y aplicaciones del producto. Elaboración de presentaciones de ventas: Ayudar a crear presentaciones visuales o informes que resalten las características y beneficios de los montacargas, adaptadas a las necesidades del cliente.\n3. Soporte en la gestión de pedidos y postventa: Realizar seguimientos después de la venta para garantizar la satisfacción del cliente y atender cualquier inquietud o problema relacionado con el producto.\n4. Actualización de CRM: Gestión de datos de clientes, Mantener actualizada la base de datos de clientes, registrando interacciones, oportunidades de ventas y otros detalles importantes en el sistema SAP.\n5. Soporte administrativo en ventas: Elaboración de informes, preparar informes sobre el desempeño de ventas, estadísticas de clientes, oportunidades de negocio y cualquier otra métrica relevante.",
          "competencies": "Responsabilidad, Compromiso, honestidad, Orientación al cliente, Comunicación efectiva y persuasiva, Negociación básica, Manejo de SAP, Organización y adaptabilidad al entorno Industrial."
        }
      ]
    },
    {
      "uuid": "38ff9991-7e80-5b4f-a066-7237ca500244",
      "listing": {
        "folio": "247036",
        "programa": "CANTAR BIEN, PARA VIVIR MEJOR",
        "tipo": "servicio_social",
        "area": "COMPLEJO CULTURAL UNIVERSITARIO",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "COMPLEJO CULTURAL UNIVERSITARIO"
      },
      "summary": {
        "tipo": "servicio_social",
        "programNumber": "247036",
        "registeredAt": "2026-09-01",
        "registeredAtRaw": "01/09/26",
        "company": "COMPLEJO CULTURAL UNIVERSITARIO",
        "sector": "UNIVERSITARIO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "CANTAR BIEN, PARA VIVIR MEJOR",
        "programType": "MULTIDISCIPLINARIO",
        "department": "COMPLEJO CULTURAL UNIVERSITARIO",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "JOSÉ ANTONIO DE LA ROSA ESPARZA",
        "position": "DIRECTOR DEL CORO SINFÓNICO BUAP",
        "email": "coro.sinfonico@correo.buap.mx",
        "phone": "2222295500 EXT 2619",
        "interviewAddress": "Vía Atlixcáyotll 2299 Puebla Puebla Cp. 72810",
        "workAddress": "Vía Atlixcáyotll 2299 Puebla Puebla Cp. 72810 Edificio de Compañías Artísticas"
      },
      "appointment": {
        "addressee": "MTRO. JOSÉ ANTONIO DE LA ROSA ESPARZA",
        "position": "DIRECTOR DEL CORO SINFÓNICO BUAP"
      },
      "programInfo": {
        "monthlyStipend": "",
        "otherSupport": "",
        "socialAxes": [],
        "promotesEntrepreneurship": false
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "",
          "competencies": ""
        }
      ]
    },
    {
      "uuid": "3ba1b287-7548-5ed3-ba01-44afd35c0451",
      "listing": {
        "folio": "247118",
        "programa": "AUXILIAR DE PROCESOS Y CALIDAD",
        "tipo": "practica_profesional",
        "area": "GOVERNANCE",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "IT SOLUTIONS GLOBAL INCORPORATED S. DE R.L."
      },
      "summary": {
        "tipo": "practica_profesional",
        "programNumber": "247118",
        "registeredAt": "2026-09-02",
        "registeredAtRaw": "02/09/26",
        "company": "IT SOLUTIONS GLOBAL INCORPORATED S. DE R.L.",
        "sector": "PRIVADO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "AUXILIAR DE PROCESOS Y CALIDAD",
        "programType": "MULTIDISCIPLINARIO",
        "department": "GOVERNANCE",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "ELIX ADRIANA TORRES SALAZAR",
        "position": "ESPECIALISTA EN RECLUTAMIENTO Y SELECCIÓN",
        "email": "reclutamientoyseleccion@itcglobals.com",
        "phone": "2224570895",
        "interviewAddress": "PROLONGACION MORELOS NÚMERO 13, COLONIA SANCTORUM, CUAUTLANCINGO",
        "workAddress": "PROLONGACION MORELOS NÚMERO 13, COLONIA SANCTORUM, CUAUTLANCINGO"
      },
      "appointment": {
        "addressee": "J. GUADALUPE MUÑOZ GRANDE",
        "position": "GERENTE DE RECURSOS HUMANOS"
      },
      "programInfo": {
        "monthlyStipend": "$1,200.00",
        "otherSupport": "NA",
        "socialAxes": [
          "Empleo justo y bien remunerado",
          "Innovación"
        ],
        "promotesEntrepreneurship": true
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "* Mantener el Sistema de Gestión de Calidad (SGC) de los procedimientos propios del sistema.\n* Establecer la metodología para la implementación, mantenimiento y mejora de los sistemas de gestión de calidad de los procesos y servicios institucionales.\n* Mantener y actualizar la documentación de acuerdo a los lineamientos establecidos; para la operación del Sistema de Gestión de Calidad (SGC).\n* Elaborar y dar el seguimiento al sistema de indicadores de calidad, con la finalidad de medir el desempeño y funcionamiento de los sistemas de gestión.\n* Organizar y supervisar la logística para la ejecución de proyectos para las auditorías de certificación y seguimiento del Sistema de Gestión de Calidad de los procesos y servicios institucionales.\n* Elaborar y promover el seguimiento al Programa Anual de Auditorías Internas.\n* Realizar las auditorías internas programadas en el año; incluyendo las reuniones con los auditores internos, elaborar de los documentos relacionados, brindar seguimiento a los resultados obtenidos para contribuir al fortalecimiento del SGC.\n* Organizar las reuniones y contenido de las juntas de Comité de Calidad y la Revisión por la Dirección.\n* Elaborar y dar seguimiento a las acciones correctivas y preventivas que resulten de las auditorías internas o externas, de revisiones por parte de la dirección, así como de las observaciones del cliente y evaluaciones de los procedimientos.\n* Brindar asesoría a las áreas del Órgano en materia de calidad y gestión administrativa, asegurando su correcta aplicación a los procesos y trámites de su ámbito.",
          "competencies": "Conocimientos y aplicación de software ISO 9001 Sistema de Gestión de Calidad Código de ética y auditorías planificación y organización eficaz\nCumplimiento de horarios identidicación de factores que pueban afectar la fiabilidaad de los hallazgos Nom 40,35"
        }
      ]
    },
    {
      "uuid": "78a14457-e3c2-57f6-b483-f2eb967091a4",
      "listing": {
        "folio": "247123",
        "programa": "GESTIÓN DE CONTRATOS, CONVENIOS Y OBLIGACIONES LEGALES EN UNA EMPRESA TURÍSTICA.",
        "tipo": "practica_profesional",
        "area": "DEPARTAMENTO JURÍDICO Y ADMINISTRATIVO.",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "SUSANA KARENINA AGUILAR HERNÁNDEZ"
      },
      "summary": {
        "tipo": "practica_profesional",
        "programNumber": "247123",
        "registeredAt": "2026-09-02",
        "registeredAtRaw": "02/09/26",
        "company": "SUSANA KARENINA AGUILAR HERNÁNDEZ",
        "sector": "PRIVADO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "GESTIÓN DE CONTRATOS, CONVENIOS Y OBLIGACIONES LEGALES EN UNA EMPRESA TURÍSTICA.",
        "programType": "MULTIDISCIPLINARIO",
        "department": "DEPARTAMENTO JURÍDICO Y ADMINISTRATIVO.",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "SUSANA KARENINA AGUILAR HERNÁNDEZ",
        "position": "DIRECTORA GENERAL",
        "email": "rhunlimitedexperiences@gmail.com",
        "phone": "2224523738",
        "interviewAddress": "3 de Mayo 216-7, Guadalupe Victoria, 72490 Heroica Puebla de Zaragoza, Pue.",
        "workAddress": "3 de Mayo 216-7, Guadalupe Victoria, 72490 Heroica Puebla de Zaragoza, Pue."
      },
      "appointment": {
        "addressee": "SUSANA KARENINA AGUILAR HERNÁNDEZ",
        "position": "DIRECTORA GENERAL"
      },
      "programInfo": {
        "monthlyStipend": "$1,200.00",
        "otherSupport": "Capacitaciones",
        "socialAxes": [
          "Empleo justo y bien remunerado"
        ],
        "promotesEntrepreneurship": false
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "El estudiante podrá colaborar en la revisión y organización de contratos; elaboración de borradores de contratos y convenios; integración y actualización de expedientes; revisión de cartas responsivas; elaboración y actualización de términos y condiciones de los diferentes servicios; apoyo en la elaboración y revisión de avisos de privacidad; investigación de legislación y disposiciones aplicables a las actividades de la empresa; control de vigencias contractuales; elaboración de formatos jurídicos internos; organización de documentación corporativa; seguimiento de convenios con proveedores, instituciones y colaboradores; apoyo en la revisión de documentos requeridos para nuevos proyectos y elaboración de reportes relacionados con obligaciones legales y administrativas.",
          "competencies": "Ética profesional, organización y análisis, aplicando conocimientos en contratos, expedientes, investigación jurídica y control documental."
        }
      ]
    },
    {
      "uuid": "81de587b-5c86-54bb-8a41-52ab695ab4f9",
      "listing": {
        "folio": "247142",
        "programa": "APOYO EN EL DESARROLLO DE HERRAMIENTAS COMPUTACIONALES PARA LA FORMACIÓN ACTUARIAL",
        "tipo": "servicio_social",
        "area": "FACULTAD FÍSICO MATEMÁTICAS",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "FACULTAD DE CS.FISICO MATEMATICAS"
      },
      "summary": {
        "tipo": "servicio_social",
        "programNumber": "247142",
        "registeredAt": "2026-09-02",
        "registeredAtRaw": "02/09/26",
        "company": "FACULTAD DE CS.FISICO MATEMATICAS",
        "sector": "UNIVERSITARIO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "APOYO EN EL DESARROLLO DE HERRAMIENTAS COMPUTACIONALES PARA LA FORMACIÓN ACTUARIAL",
        "programType": "MULTIDISCIPLINARIO",
        "department": "FACULTAD FÍSICO MATEMÁTICAS",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "GABRIEL CAO ROMERO MARTÍNEZ",
        "position": "DOCENTE",
        "email": "gcaoromero@gmail.com",
        "phone": "2224692635",
        "interviewAddress": "via correo",
        "workAddress": "facultad de ciencias físico matemáticas"
      },
      "appointment": {
        "addressee": "GABRIEL CAO ROMERO MARTÍNEZ",
        "position": "PROFESOR"
      },
      "programInfo": {
        "monthlyStipend": "",
        "otherSupport": "",
        "socialAxes": [],
        "promotesEntrepreneurship": false
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "",
          "competencies": ""
        }
      ]
    },
    {
      "uuid": "1564912a-2359-5b87-bc2e-07cf0ba9cae1",
      "listing": {
        "folio": "247143",
        "programa": "PROGRAMA DE EXPERIENCIA PROFESIONAL APLICADA",
        "tipo": "practica_profesional",
        "area": "FACULTAD FÍSICO MATEMÁTICAS",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "FACULTAD DE CS.FISICO MATEMATICAS"
      },
      "summary": {
        "tipo": "practica_profesional",
        "programNumber": "247143",
        "registeredAt": "2026-09-02",
        "registeredAtRaw": "02/09/26",
        "company": "FACULTAD DE CS.FISICO MATEMATICAS",
        "sector": "UNIVERSITARIO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "PROGRAMA DE EXPERIENCIA PROFESIONAL APLICADA",
        "programType": "MULTIDISCIPLINARIO",
        "department": "FACULTAD FÍSICO MATEMÁTICAS",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "GABRIEL CAO ROMERO MARTÍNEZ",
        "position": "DOCENTE",
        "email": "gcaoromero@gmail.com",
        "phone": "2224692635",
        "interviewAddress": "via correo",
        "workAddress": "facultad de ciencias físico matemáticas"
      },
      "appointment": {
        "addressee": "GABRIEL CAO ROMERO MARTÍNEZ",
        "position": "DOCENTE"
      },
      "programInfo": {
        "monthlyStipend": "$.00",
        "otherSupport": "NA",
        "socialAxes": [
          "Innovación"
        ],
        "promotesEntrepreneurship": true
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "Apoyo en la elaboración y organización de material académico y didáctico.\nParticipación en actividades de investigación, análisis y desarrollo de contenidos educativos.\nColaboración en la planeación y seguimiento de actividades académicas y de capacitación.\nUso de herramientas tecnológicas y software para el análisis y procesamiento de información.\nElaboración de reportes, presentaciones y documentos de apoyo para actividades del programa.\nApoyo en la atención y acompañamiento de estudiantes durante sesiones y actividades académicas.\nDesarrollo de ejercicios prácticos y actividades orientadas al fortalecimiento de competencias analíticas y profesionales.\nParticipación en proyectos de análisis de datos y resolución de problemáticas aplicadas.\nColaboración en actividades de mejora e innovación educativa.\nIntegración y trabajo colaborativo en equipos académicos y multidisciplinarios.",
          "competencies": "Entre las competencias genéricas, se busca desarrollar habilidades de análisis, pensamiento crítico y resolución de problemas, así como capacidades de comunicación oral y escrita, trabajo en equipo, organización y responsabilidad profesional. Asimismo, se fomentarán valores y actitudes como el compr"
        }
      ]
    },
    {
      "uuid": "a2805c7c-377f-5255-a34a-9687f653a29d",
      "listing": {
        "folio": "247146",
        "programa": "PROGRAMA DE MEJORA DEL PROCESO DE ENSEÑANZA-APRENDIZAJE DE LA UNIVERSIDAD",
        "tipo": "servicio_social",
        "area": "FACULTAD DE FÍSICO- MATEMÁTICAS",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "FACULTAD DE CS.FISICO MATEMATICAS"
      },
      "summary": {
        "tipo": "servicio_social",
        "programNumber": "247146",
        "registeredAt": "2026-09-02",
        "registeredAtRaw": "02/09/26",
        "company": "FACULTAD DE CS.FISICO MATEMATICAS",
        "sector": "UNIVERSITARIO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "PROGRAMA DE MEJORA DEL PROCESO DE ENSEÑANZA-APRENDIZAJE DE LA UNIVERSIDAD",
        "programType": "MULTIDISCIPLINARIO",
        "department": "FACULTAD DE FÍSICO- MATEMÁTICAS",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "REYNALDO SOTO LOZANO",
        "position": "DOCENTE",
        "email": "reynaldo.soto@correo.buap.mx",
        "phone": "2221252659",
        "interviewAddress": "Ciudad Universitaria",
        "workAddress": "Ciudad Universitaria"
      },
      "appointment": {
        "addressee": "REYNALDO SOTO LOZANO",
        "position": "DOCENTE"
      },
      "programInfo": {
        "monthlyStipend": "",
        "otherSupport": "",
        "socialAxes": [],
        "promotesEntrepreneurship": false
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "",
          "competencies": ""
        }
      ]
    },
    {
      "uuid": "c6afc7b5-d7e4-5ca6-bc3d-fb6ec392d475",
      "listing": {
        "folio": "247162",
        "programa": "GESTIÓN, ANÁLISIS Y ADMINISTRACIÓN DE SEGUROS Y FIANZAS",
        "tipo": "practica_profesional",
        "area": "ÁREA ADMINISTRATIVA",
        "perfilEducativo": "Lic. en Actuaría",
        "coordinador": "XOCHIPA - PEREZ ITZEL",
        "cursoInduccion": "Curso(s)",
        "empresa": "SEGFIANZ CONSULTORES, AGENTE DE SEGUROS Y DE FIANZAS, S.A. DE C.V.,"
      },
      "summary": {
        "tipo": "practica_profesional",
        "programNumber": "247162",
        "registeredAt": "2026-09-02",
        "registeredAtRaw": "02/09/26",
        "company": "SEGFIANZ CONSULTORES, AGENTE DE SEGUROS Y DE FIANZAS, S.A. DE C.V.,",
        "sector": "PRIVADO",
        "period": "1, 2027",
        "revalidated": false,
        "status": "ACEPTADO"
      },
      "general": {
        "name": "GESTIÓN, ANÁLISIS Y ADMINISTRACIÓN DE SEGUROS Y FIANZAS",
        "programType": "MULTIDISCIPLINARIO",
        "department": "ÁREA ADMINISTRATIVA",
        "startDate": "2027-01-05",
        "startDateRaw": "05/01/27",
        "endDate": "2027-07-05",
        "endDateRaw": "05/07/27",
        "durationMonths": 6
      },
      "supervisor": {
        "name": "ESTHER ALMAZAN TORRES",
        "position": "CEO",
        "email": "segurosyfianzas@segfianzconsultores.com",
        "phone": "2227363020",
        "interviewAddress": "TERCERA PRIVADA C 23 SUR 2116 INT 7A COLONIA LA NORIA",
        "workAddress": "TERCERA PRIVADA C 23 SUR 2116 INT 7A COLONIA LA NORIA"
      },
      "appointment": {
        "addressee": "ESTHER ALMAZAN TORRES",
        "position": "REPRESENTANTE LEGAL"
      },
      "programInfo": {
        "monthlyStipend": "$1,200.00",
        "otherSupport": ".",
        "socialAxes": [
          "Empleo justo y bien remunerado"
        ],
        "promotesEntrepreneurship": true
      },
      "areaDetails": [
        {
          "areaUuid": "25d628fe-d316-59e0-846d-2518bb2250f3",
          "activities": "Gestión, Análisis y Administración de Seguros y Fianzas: Brindar al estudiante la oportunidad de desarrollar y aplicar los conocimientos adquiridos durante su formación profesional mediante su participación en actividades relacionadas con la administración, análisis, operación, gestión documental y seguimiento de operaciones de seguros y fianzas, fortaleciendo sus competencias profesionales, analíticas, administrativas y jurídicas en un entorno laboral. --Actividades generales del programa\nApoyo en la integración, organización y actualización de expedientes de seguros y fianzas.\nCaptura, revisión y actualización de información en bases de datos.\nElaboración de reportes y controles administrativos.\nApoyo en la revisión y análisis de pólizas, fianzas, cotizaciones y documentación relacionada.\nElaboración de comparativos de propuestas de seguros.\nApoyo en el análisis de información financiera, estadística y administrativa.\nRevisión de documentación contractual y requisitos administrativos.\nApoyo en el seguimiento de trámites ante instituciones aseguradoras y afianzadoras.\nOrganización y control de documentación física y digital.\nElaboración de documentos, reportes y controles internos.\nApoyo en procesos de atención y seguimiento a clientes.\nParticipación en proyectos de mejora y optimización de procesos internos. Elaboración y actualización de bases de datos.\nDesarrollo de indicadores para apoyo en la toma de decisiones.",
          "competencies": "Desarrollar competencias genéricas como responsabilidad, organización, trabajo en equipo, comunicación efectiva, pensamiento analítico y crítico, resolución de problemas, atención al detalle, ética profesional, confidencialidad, iniciativa y capacidad de adaptación al entorno laboral."
        }
      ]
    }
  ],
  "requests": [
    {
      "stage": "careers",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/ss_oferta_ss?se=ABE63459925DAD50",
      "parameters": {},
      "httpStatus": 200,
      "durationSeconds": 2.305,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "listing",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_prog",
      "parameters": {
        "un": "0FB43CD29E3E98C8",
        "se": "CF593C89C3F382C4"
      },
      "httpStatus": 200,
      "durationSeconds": 1.799,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "98B8D431BACE8367",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.519,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "44CBA431E3E63250",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.469,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "AE0A76C710C5061E",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.526,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "8D4165E288B50160",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.519,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "CC8E8A05BB5DA030",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.512,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "41F28DFA654340AD",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.536,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "FD78C899FB6889FA",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.517,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "8CC9DF0E5FA270AB",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.473,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "B7633E5243D047C6",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.515,
      "error": null,
      "responseExcerpt": null
    },
    {
      "stage": "detail",
      "url": "http://webserver.siiaa.siu.buap.mx/serv_social/Ss_OFERTA_CAR_PROG",
      "parameters": {
        "v_01": "8D1526258D67194D",
        "ca": "040DADDB4F6FCC84"
      },
      "httpStatus": 200,
      "durationSeconds": 0.516,
      "error": null,
      "responseExcerpt": null
    }
  ]
}
```
