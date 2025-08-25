{
    'name': 'Purchase Cascading Discounts',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Aplica múltiples descuentos en cascada para proveedores',
    'description': """
        Purchase Cascading Discounts
        =============================
        
        Este módulo permite configurar y aplicar hasta 4 descuentos en cascada
        en las tarifas de proveedor, que se aplicarán automáticamente en los
        pedidos de compra.
        
        Características principales:
        ----------------------------
        * Configuración de hasta 4 descuentos por proveedor/producto
        * Cálculo automático en cascada (cada descuento se aplica sobre el saldo del anterior)
        * Trazabilidad completa de descuentos aplicados en pedidos de compra
        * Integración transparente con el flujo de compras estándar
        
        Configuración:
        -------------
        1. Vaya a la ficha del producto > pestaña Compra
        2. Configure los descuentos en las tarifas de proveedor
        3. Los descuentos se aplicarán automáticamente al crear pedidos de compra
    """,
    'author': 'ITOnline - Victor Rodarte',
    'website': 'https://www.itonline.com.mx',
    'depends': [
        'purchase',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/purchase_order_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}