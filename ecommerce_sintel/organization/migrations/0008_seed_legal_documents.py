"""
White-label F5 (2026-08-14): siembra organization.LegalDocument con el texto
EXACTO que ya vivia hardcodeado en frontend/src/components/auth/kyc/legalDocs.js
(mismo docType, mismo heading/paragraphs/list por seccion, mismos valores de
EMPRESA ya interpolados). No se inventa ni reescribe ningun contenido legal --
esto es una migracion de "donde vive el dato", no un cambio de "que dice el
dato". El placeholder de razon social/NIT sin resolver se preserva tal cual
(ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_BUSINESS_RULE_CATALOG.md seccion 6).

Tras esta migracion, legalDocs.js pasa a ser codigo muerto (el frontend
consume esto via API) pero el archivo JS no se borra en esta misma fase --
ver nota en el commit/roadmap sobre F7.
"""
from django.db import migrations

UPDATED = '10 de julio de 2026'

EMPRESA = {
    'nombre': 'Sintel',
    'razonSocial': 'Sintel Corp [PENDIENTE: razon social exacta segun Camara de Comercio]',
    'nit': '[PENDIENTE: NIT registrado ante la DIAN]',
    'email': 'info@sintel.net.co',
    'telefono': '+57 300 123 4567',
    'direccion': 'Colombia -- servicio a nivel nacional',
    'sitio': 'sintel.net.co',
}


def _build_docs():
    return {
        'terminos': {
            'title': 'Terminos y Condiciones',
            'sections': [
                {
                    'heading': '1. Identificacion del prestador',
                    'paragraphs': [
                        f"<strong>{EMPRESA['razonSocial']}</strong> (en adelante, \"Sintel\"), NIT {EMPRESA['nit']}, con domicilio en {EMPRESA['direccion']}, es responsable de la plataforma de comercio electronico disponible en <strong>{EMPRESA['sitio']}</strong>, dedicada a la venta de productos, alquiler de equipos, prestacion de servicios tecnicos y elaboracion de cotizaciones.",
                        f"Datos de contacto: correo electronico {EMPRESA['email']}, telefono {EMPRESA['telefono']}.",
                    ],
                },
                {
                    'heading': '2. Objeto y aceptacion',
                    'paragraphs': [
                        'Estos Terminos y Condiciones regulan el acceso y uso de la plataforma Sintel por parte de cualquier usuario, ya sea comprador, arrendatario, solicitante de servicios o visitante. El registro en la plataforma o la realizacion de cualquier compra, solicitud de alquiler o de servicio implica la aceptacion plena de estos terminos.',
                        'Si el usuario no esta de acuerdo con alguna disposicion aqui contenida, debe abstenerse de usar la plataforma.',
                    ],
                },
                {
                    'heading': '3. Registro de usuario',
                    'paragraphs': [
                        'El usuario se compromete a suministrar informacion veraz, completa y actualizada al momento de registrarse. Sintel podra verificar la identidad de los usuarios (proceso de verificacion KYC) conforme a su politica interna de prevencion de fraude, especialmente para usuarios que soliciten actuar como proveedores, contratistas o transportistas dentro de la plataforma.',
                        'El usuario es responsable de mantener la confidencialidad de sus credenciales de acceso y de toda actividad realizada desde su cuenta.',
                    ],
                },
                {
                    'heading': '4. Productos y servicios ofrecidos',
                    'paragraphs': [
                        'A traves de la plataforma, Sintel ofrece: (i) venta de productos por catalogo; (ii) alquiler de equipos y herramientas; (iii) servicios tecnicos especializados; y (iv) cotizaciones personalizadas para proyectos. Cada modalidad puede tener condiciones comerciales especificas, informadas en el detalle de cada producto, equipo o servicio antes de confirmar la transaccion.',
                    ],
                },
                {
                    'heading': '5. Precios y medios de pago',
                    'paragraphs': [
                        'Los precios publicados en la plataforma estan expresados en pesos colombianos (COP) e incluyen los impuestos aplicables (IVA), salvo que se indique expresamente lo contrario. El costo de envio, cuando aplique, se informa antes de la confirmacion del pedido.',
                        'Los pagos se procesan a traves de la pasarela de pagos Wompi Colombia, que cumple con los estandares de seguridad PCI-DSS. Sintel no almacena directamente los datos completos de tarjetas de credito o debito de los usuarios.',
                    ],
                },
                {
                    'heading': '6. Proceso de compra, alquiler y solicitud de servicios',
                    'paragraphs': [
                        'La confirmacion de un pedido, solicitud de alquiler o solicitud de servicio esta sujeta a la disponibilidad real del producto, equipo o profesional al momento del pago. En caso de no disponibilidad, Sintel informara al usuario y procedera al reembolso correspondiente conforme a la Politica de Devoluciones.',
                    ],
                },
                {
                    'heading': '7. Envios y entregas',
                    'paragraphs': [
                        'Los plazos de entrega estimados se informan en el proceso de compra y pueden variar segun la ubicacion del usuario y la disponibilidad del producto. Sintel no es responsable por retrasos atribuibles a la empresa transportadora, casos fortuitos o de fuerza mayor.',
                    ],
                },
                {
                    'heading': '8. Derecho de retracto y garantias',
                    'paragraphs': [
                        'El usuario cuenta con el derecho de retracto establecido en el articulo 47 de la Ley 1480 de 2011 para compras realizadas a distancia, y con las garantias legales establecidas en los articulos 7 a 18 de la misma ley. Las condiciones detalladas de ambos derechos se encuentran en la <strong>Politica de Devoluciones</strong> y la <strong>Politica de Garantia</strong>, disponibles en el pie de pagina de la plataforma.',
                    ],
                },
                {
                    'heading': '9. Propiedad intelectual',
                    'paragraphs': [
                        'Todos los contenidos de la plataforma (marca, logotipos, textos, imagenes, disenio y software) son propiedad de Sintel o de sus licenciantes y estan protegidos por la normativa de propiedad intelectual vigente en Colombia. Queda prohibida su reproduccion total o parcial sin autorizacion expresa.',
                    ],
                },
                {
                    'heading': '10. Responsabilidad',
                    'paragraphs': [
                        'Sintel actua con la diligencia debida en la operacion de la plataforma, pero no garantiza la disponibilidad ininterrumpida del servicio. Sintel no sera responsable por danios derivados del uso indebido de la plataforma por parte del usuario, ni por el contenido publicado por terceros (proveedores, contratistas) que participan en el ecosistema.',
                    ],
                },
                {
                    'heading': '11. Proteccion de datos personales',
                    'paragraphs': [
                        'El tratamiento de los datos personales suministrados por el usuario se rige por la <strong>Politica de Privacidad y Tratamiento de Datos Personales</strong> de Sintel, elaborada conforme a la Ley 1581 de 2012 y el Decreto 1377 de 2013, disponible en el pie de pagina de la plataforma.',
                    ],
                },
                {
                    'heading': '12. Peticiones, quejas y reclamos (PQR)',
                    'paragraphs': [
                        f"El usuario puede presentar peticiones, quejas o reclamos a traves del correo {EMPRESA['email']} o del canal de soporte dentro de la plataforma. Sintel dara respuesta dentro de los plazos establecidos por la ley. En caso de no obtener una respuesta satisfactoria, el usuario puede acudir a la <strong>Superintendencia de Industria y Comercio (SIC)</strong> como autoridad de proteccion al consumidor en Colombia.",
                    ],
                },
                {
                    'heading': '13. Ley aplicable y jurisdiccion',
                    'paragraphs': [
                        'Estos Terminos y Condiciones se rigen por las leyes de la Republica de Colombia. Cualquier controversia derivada de su interpretacion o ejecucion sera resuelta ante los jueces competentes de Colombia, sin perjuicio de los mecanismos de proteccion al consumidor establecidos por la ley.',
                    ],
                },
                {
                    'heading': '14. Modificaciones',
                    'paragraphs': [
                        'Sintel podra modificar estos Terminos y Condiciones en cualquier momento. Los cambios se publicaran en esta misma seccion, indicando la fecha de la ultima actualizacion. El uso continuado de la plataforma despues de una modificacion implica la aceptacion de los nuevos terminos.',
                    ],
                },
            ],
        },
        'politica': {
            'title': 'Politica de Privacidad y Tratamiento de Datos Personales',
            'sections': [
                {
                    'heading': '1. Responsable del tratamiento',
                    'paragraphs': [
                        f"{EMPRESA['razonSocial']}, NIT {EMPRESA['nit']}, con domicilio en {EMPRESA['direccion']} y correo de contacto {EMPRESA['email']}, es responsable del tratamiento de los datos personales recolectados a traves de la plataforma {EMPRESA['sitio']}, en cumplimiento de la Ley 1581 de 2012, el Decreto 1377 de 2013 y demas normas concordantes sobre proteccion de datos personales en Colombia.",
                    ],
                },
                {
                    'heading': '2. Finalidad del tratamiento',
                    'list': [
                        'Gestionar el registro y la autenticacion de la cuenta del usuario.',
                        'Verificar la identidad del usuario (proceso KYC) cuando aplique, con fines de prevencion de fraude.',
                        'Procesar pedidos, pagos, solicitudes de alquiler y de servicios tecnicos.',
                        'Enviar comunicaciones relacionadas con el estado de pedidos, solicitudes o cotizaciones.',
                        'Enviar comunicaciones comerciales, unicamente si el usuario ha autorizado expresamente recibirlas.',
                        'Dar cumplimiento a obligaciones legales y contractuales.',
                    ],
                },
                {
                    'heading': '3. Datos recolectados',
                    'paragraphs': [
                        'Segun el tipo de interaccion del usuario con la plataforma, Sintel podra recolectar: datos de identificacion (nombre, documento de identidad), datos de contacto (correo, telefono, direccion), datos transaccionales (historial de compras, alquileres y servicios) y, cuando el usuario solicite actuar como proveedor o contratista, documentos de verificacion de identidad.',
                    ],
                },
                {
                    'heading': '4. Derechos del titular de los datos',
                    'paragraphs': [
                        'Conforme al articulo 8 de la Ley 1581 de 2012, el titular de los datos personales tiene derecho a:',
                    ],
                    'list': [
                        'Conocer, actualizar y rectificar sus datos personales.',
                        'Solicitar prueba de la autorizacion otorgada para el tratamiento de sus datos.',
                        'Ser informado sobre el uso que se ha dado a sus datos personales.',
                        'Presentar quejas ante la Superintendencia de Industria y Comercio por infracciones a la ley.',
                        'Revocar la autorizacion y/o solicitar la supresion de sus datos, cuando no exista un deber legal o contractual que lo impida.',
                        'Acceder de forma gratuita a sus datos personales que hayan sido objeto de tratamiento.',
                    ],
                },
                {
                    'heading': '5. Como ejercer estos derechos',
                    'paragraphs': [
                        f"El titular puede ejercer sus derechos enviando una solicitud al correo electronico {EMPRESA['email']}, indicando su nombre completo, numero de documento y la solicitud concreta. Sintel dara respuesta dentro de los plazos establecidos en la ley (10 dias habiles para consultas, 15 dias habiles para reclamos).",
                    ],
                },
                {
                    'heading': '6. Transferencia y transmision de datos a terceros',
                    'paragraphs': [
                        'Para el procesamiento de pagos, los datos necesarios se comparten con la pasarela de pagos Wompi Colombia, bajo sus propias politicas de tratamiento de datos y estandares de seguridad. Sintel podra tambien compartir datos con empresas de transporte y logistica, unicamente para efectos de entrega de pedidos, y con proveedores tecnologicos que prestan servicios de infraestructura, bajo acuerdos de confidencialidad.',
                    ],
                },
                {
                    'heading': '7. Seguridad de la informacion',
                    'paragraphs': [
                        'Sintel implementa medidas tecnicas, humanas y administrativas razonables para proteger los datos personales de los usuarios contra perdida, uso indebido, acceso no autorizado, alteracion o divulgacion, incluyendo cifrado en transito (HTTPS/TLS) en toda la plataforma.',
                    ],
                },
                {
                    'heading': '8. Vigencia',
                    'paragraphs': [
                        'Los datos personales se conservaran durante el tiempo necesario para cumplir con las finalidades del tratamiento y con las obligaciones legales, contables y fiscales aplicables. Esta politica rige a partir de su fecha de publicacion y podra ser actualizada en cualquier momento.',
                    ],
                },
            ],
        },
        'garantia': {
            'title': 'Politica de Garantia',
            'sections': [
                {
                    'heading': '1. Garantia legal',
                    'paragraphs': [
                        'De conformidad con los articulos 7 a 18 de la Ley 1480 de 2011 (Estatuto del Consumidor), todos los productos y equipos ofrecidos a traves de Sintel cuentan con garantia legal frente a defectos que tengan relacion con la calidad, idoneidad o seguridad del producto, sin perjuicio de la garantia adicional que pueda ofrecer el fabricante.',
                        'El termino de la garantia legal, salvo que se indique un plazo mayor en la ficha del producto, es de un (1) año contado a partir de la entrega, o el que informe el fabricante si es superior.',
                    ],
                },
                {
                    'heading': '2. Cobertura',
                    'list': [
                        'Defectos de fabricacion que afecten el funcionamiento normal del producto o equipo.',
                        'No conformidad entre el producto entregado y lo ofrecido en la publicacion.',
                        'En el caso de equipos en alquiler: fallas mecanicas o electricas no atribuibles al uso indebido por parte del arrendatario.',
                    ],
                },
                {
                    'heading': '3. Exclusiones de garantia',
                    'list': [
                        'Danios ocasionados por uso indebido, negligencia o incumplimiento de las instrucciones de uso.',
                        'Desgaste normal por el uso del producto o equipo.',
                        'Modificaciones o reparaciones realizadas por personal no autorizado por Sintel o el fabricante.',
                        'Danios ocasionados por accidentes, caso fortuito o fuerza mayor.',
                    ],
                },
                {
                    'heading': '4. Procedimiento para hacer efectiva la garantia',
                    'paragraphs': [
                        f"Para solicitar la garantia, el usuario debe contactar a Sintel a traves del correo {EMPRESA['email']} o el canal de soporte de la plataforma, indicando el numero de pedido u orden, la descripcion del defecto y, de ser posible, evidencia fotografica o en video.",
                        'Sintel evaluara la solicitud y, de proceder, coordinara segun el caso: la reparacion, el cambio del producto o equipo, o el reembolso del dinero pagado, sin costo adicional para el usuario.',
                    ],
                },
                {
                    'heading': '5. Plazos de respuesta',
                    'paragraphs': [
                        'Sintel dara respuesta a las solicitudes de garantia dentro de los quince (15) dias habiles siguientes a su radicacion, conforme al articulo 58 de la Ley 1480 de 2011.',
                    ],
                },
                {
                    'heading': '6. Garantia en servicios tecnicos',
                    'paragraphs': [
                        'Los servicios tecnicos prestados a traves de la plataforma cuentan con garantia sobre la mano de obra realizada, en los terminos especificos informados por el prestador del servicio al momento de la contratacion. Esta garantia no cubre danios posteriores derivados de un uso inadecuado del bien intervenido.',
                    ],
                },
            ],
        },
        'devoluciones': {
            'title': 'Politica de Devoluciones y Derecho de Retracto',
            'sections': [
                {
                    'heading': '1. Derecho de retracto',
                    'paragraphs': [
                        'De conformidad con el articulo 47 de la Ley 1480 de 2011, por tratarse de ventas realizadas a traves de un medio no tradicional (comercio electronico), el usuario tiene derecho a retractarse de su compra dentro de los <strong>cinco (5) dias habiles</strong> siguientes a la entrega del producto, sin necesidad de justificar su decision.',
                    ],
                },
                {
                    'heading': '2. Productos y servicios excluidos del retracto',
                    'paragraphs': [
                        'Conforme al paragrafo del articulo 47 de la Ley 1480 de 2011, el derecho de retracto no aplica, entre otros casos, a:',
                    ],
                    'list': [
                        'Productos elaborados conforme a las especificaciones del usuario o claramente personalizados.',
                        'Servicios ya prestados en su totalidad, cuando el usuario haya aceptado expresamente su ejecucion antes de finalizar el plazo de retracto.',
                        'Bienes que, por su naturaleza, no puedan devolverse (ej. deteriorados o manipulados fuera del uso normal para verificar su naturaleza y funcionamiento).',
                    ],
                },
                {
                    'heading': '3. Procedimiento para ejercer el retracto',
                    'paragraphs': [
                        f"El usuario debe informar su decision de retractarse a traves del correo {EMPRESA['email']} o el canal de soporte de la plataforma, dentro del plazo indicado, adjuntando el numero de pedido. El producto debe devolverse en las mismas condiciones en que fue entregado, con su empaque original y accesorios, cuando aplique.",
                    ],
                },
                {
                    'heading': '4. Devoluciones por producto defectuoso o no conforme',
                    'paragraphs': [
                        'Si el producto llega defectuoso, incompleto o no corresponde a lo solicitado, el usuario puede solicitar el cambio o la devolucion del dinero, conforme a lo establecido en la Politica de Garantia, sin que le sean aplicables los plazos ni exclusiones del derecho de retracto.',
                    ],
                },
                {
                    'heading': '5. Reembolsos',
                    'paragraphs': [
                        'Una vez aceptada la devolucion, Sintel procesara el reembolso a traves del mismo medio de pago utilizado en la compra original, dentro de un plazo maximo de treinta (30) dias calendario, conforme al Estatuto del Consumidor.',
                    ],
                },
                {
                    'heading': '6. Costos de devolucion',
                    'paragraphs': [
                        'Cuando la devolucion se origine por ejercicio del derecho de retracto, los costos de envio de la devolucion corren por cuenta del usuario, salvo que la ley disponga lo contrario. Cuando la devolucion se origine por un defecto o error atribuible a Sintel, los costos de envio de la devolucion seran asumidos por Sintel.',
                    ],
                },
            ],
        },
        'autorizacion': {
            'title': 'Autorizacion de Tratamiento de Datos',
            'sections': [
                {
                    'heading': None,
                    'paragraphs': [
                        f"Al continuar, autorizo de manera libre, expresa e informada a {EMPRESA['razonSocial']} para recolectar, almacenar, usar y procesar mis datos personales, incluidos los documentos de identidad que suministre durante el proceso de verificacion, unicamente para los fines de validacion de identidad, prevencion de fraude y operacion de la plataforma, en los terminos descritos en la Politica de Privacidad y Tratamiento de Datos Personales.",
                    ],
                },
            ],
        },
    }


def seed_legal_documents(apps, schema_editor):
    LegalDocument = apps.get_model('organization', 'LegalDocument')
    for doc_type, doc in _build_docs().items():
        LegalDocument.objects.get_or_create(
            doc_type=doc_type,
            defaults={
                'title': doc['title'],
                'updated_label': UPDATED,
                'sections': doc['sections'],
                'is_active': True,
            },
        )


def unseed_legal_documents(apps, schema_editor):
    LegalDocument = apps.get_model('organization', 'LegalDocument')
    LegalDocument.objects.filter(doc_type__in=list(_build_docs().keys())).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0007_legaldocument'),
    ]

    operations = [
        migrations.RunPython(seed_legal_documents, unseed_legal_documents),
    ]
