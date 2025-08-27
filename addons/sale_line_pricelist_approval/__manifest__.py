# -*- coding: utf-8 -*-
{
    'name': 'Sale Line Pricelist Approval',
    'version': '18.0.1.0.0',
    'summary': 'Permite selección de precios por línea de pedido con flujo de aprobación',
    'description': """
        Módulo de Precios por Partida y Flujo de Aprobación
        =====================================================
        
        Este módulo permite:
        - Seleccionar diferentes listas de precios por cada línea de pedido
        - Establecer precios manuales que requieren aprobación
        - Flujo de aprobación integrado para precios especiales
        - Trazabilidad completa de aprobaciones
        
        Características principales:
        - 3 listas de precios predefinidas por línea
        - Opción de precio manual con aprobación obligatoria
        - Estados de aprobación por línea
        - Notificaciones automáticas a aprobadores
        - Registro de auditoría en el chatter
    """,
    'category': 'Sales/Sales',
    'author': 'ITOnline - Victor Rodarte',
    'website': 'https://www.itonline.com.mx',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'mail',
        'product',
    ],
    'data': [
        'security/sale_line_pricelist_security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'data/pricelist_data.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'sale_line_pricelist_approval/static/src/js/sale_order_form.js',
        ],
    },
}