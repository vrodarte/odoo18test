# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    # Campos para mostrar los descuentos que fueron aplicados desde la tarifa
    applied_discount_1 = fields.Float(
        string='Desc. 1 (%)',
        digits='Discount',
        help="Primer descuento aplicado desde la tarifa del proveedor"
    )
    
    applied_discount_2 = fields.Float(
        string='Desc. 2 (%)',
        digits='Discount',
        help="Segundo descuento aplicado desde la tarifa del proveedor"
    )
    
    applied_discount_3 = fields.Float(
        string='Desc. 3 (%)',
        digits='Discount',
        help="Tercer descuento aplicado desde la tarifa del proveedor"
    )
    
    applied_discount_4 = fields.Float(
        string='Desc. 4 (%)',
        digits='Discount',
        help="Cuarto descuento aplicado desde la tarifa del proveedor"
    )
    
    # Campo para mostrar el precio antes de descuentos
    price_before_discount = fields.Float(
        string='Precio Original',
        readonly=True,
        digits='Product Price',
        help="Precio original antes de aplicar los descuentos en cascada"
    )
    
    @api.onchange('product_id')
    def _onchange_product_id_cascade_discounts(self):
        """
        Aplica los descuentos en cascada cuando se selecciona un producto
        en el pedido de compra.
        """
        if not self.product_id or not self.order_id or not self.order_id.partner_id:
            return
        
        # 2. Buscar la tarifa de proveedor relevante
        params = {'partner_id': self.order_id.partner_id}
        seller = self.product_id._select_seller(
            partner_id=self.order_id.partner_id,
            quantity=self.product_qty,
            date=self.date_planned and self.date_planned.date(),
            uom_id=self.product_uom,
            params=params
        )
        
        if seller:
            # 3. Obtener el precio base y los descuentos configurados
            price = seller.price
            
            # Guardar el precio original
            self.price_before_discount = price
            
            # Obtener los descuentos (verificar si existen los campos)
            discounts = []
            discount_fields = [
                ('discount1', 'applied_discount_1'),
                ('discount2', 'applied_discount_2'),
                ('discount3', 'applied_discount_3'),
                ('discount4', 'applied_discount_4')
            ]
            
            # 4. Aplicar los descuentos en cascada
            for field_name, applied_field in discount_fields:
                disc_value = 0.0
                if hasattr(seller, field_name):
                    disc_value = getattr(seller, field_name, 0.0) or 0.0
                
                setattr(self, applied_field, disc_value)
            
            # 5. Calcular el precio final usando la función auxiliar
            self._calculate_final_price_from_discounts()
            
            # Log para debugging
            _logger.info(
                'Descuentos en cascada aplicados: Producto=%s, Proveedor=%s, '
                'Precio Original=%.2f, Precio Final=%.2f, '
                'Descuentos=[%.2f%%, %.2f%%, %.2f%%, %.2f%%]',
                self.product_id.name,
                self.order_id.partner_id.name,
                price,
                self.price_unit,
                self.applied_discount_1,
                self.applied_discount_2,
                self.applied_discount_3,
                self.applied_discount_4
            )
        else:
            # Limpiar campos si no hay tarifa de proveedor
            self.applied_discount_1 = 0.0
            self.applied_discount_2 = 0.0
            self.applied_discount_3 = 0.0
            self.applied_discount_4 = 0.0
            self.price_before_discount = 0.0
    
    @api.onchange('product_qty', 'product_uom', 'date_planned')
    def _onchange_cascade_params(self):
        """
        Re-aplica los descuentos cuando cambian parámetros que podrían
        afectar la selección de la tarifa del proveedor.
        """
        if self.product_id and self.order_id and self.order_id.partner_id:
            self._onchange_product_id_cascade_discounts()
    
    @api.onchange('applied_discount_1', 'applied_discount_2', 'applied_discount_3', 'applied_discount_4')
    def _onchange_manual_discounts(self):
        """
        Recalcula el precio final cuando se modifican manualmente los descuentos.
        """
        if self.price_before_discount > 0:
            self._calculate_final_price_from_discounts()
    
    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        """
        Cuando se modifica manualmente el precio unitario, actualizar el precio base
        para que los cálculos de descuento funcionen correctamente.
        """
        # Si no hay precio base registrado, usar el precio actual como base
        if not self.price_before_discount and self.price_unit:
            self.price_before_discount = self.price_unit
            # Limpiar descuentos si se establece un precio manual
            self.applied_discount_1 = 0.0
            self.applied_discount_2 = 0.0
            self.applied_discount_3 = 0.0
            self.applied_discount_4 = 0.0
    
    def _calculate_final_price_from_discounts(self):
        """
        Calcula el precio final aplicando los descuentos en cascada
        al precio antes de descuentos.
        """
        if not self.price_before_discount:
            return
        
        # Aplicar descuentos en cascada
        final_price = self.price_before_discount
        discounts = [
            self.applied_discount_1 or 0.0,
            self.applied_discount_2 or 0.0,
            self.applied_discount_3 or 0.0,
            self.applied_discount_4 or 0.0
        ]
        
        for discount in discounts:
            if discount > 0:
                final_price *= (1 - (discount / 100.0))
        
        # Actualizar el precio unitario
        self.price_unit = final_price
        
        # Log para debugging
        _logger.info(
            'Descuentos manuales aplicados: Producto=%s, '
            'Precio Original=%.2f, Precio Final=%.2f, '
            'Descuentos=[%.2f%%, %.2f%%, %.2f%%, %.2f%%]',
            self.product_id.name or 'N/A',
            self.price_before_discount,
            final_price,
            self.applied_discount_1,
            self.applied_discount_2,
            self.applied_discount_3,
            self.applied_discount_4
        )
    
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        """
        Hereda el cálculo del monto para asegurar que funcione correctamente
        con los descuentos en cascada ya aplicados en price_unit
        """
        res = super()._compute_amount()
        return res
    
    @api.constrains('applied_discount_1', 'applied_discount_2', 'applied_discount_3', 'applied_discount_4')
    def _check_discount_values(self):
        """
        Valida que los descuentos estén en un rango válido (0-100%).
        """
        for line in self:
            discounts = [
                line.applied_discount_1,
                line.applied_discount_2,
                line.applied_discount_3,
                line.applied_discount_4
            ]
            for i, discount in enumerate(discounts, 1):
                if discount < 0 or discount > 100:
                    raise ValidationError(
                        _('El descuento %d debe estar entre 0%% y 100%%. '
                          'Valor actual: %.2f%%') % (i, discount)
                    )