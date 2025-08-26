# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools import float_compare


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    # Campos para los descuentos en cascada
    discount1 = fields.Float(
        string='Desc. 1 (%)',
        digits='Discount',
        default=0.0,
        help="Primer descuento en cascada aplicado al precio del proveedor."
    )

    discount2 = fields.Float(
        string='Desc. 2 (%)',
        digits='Discount',
        default=0.0,
        help="Segundo descuento en cascada aplicado al precio del proveedor."
    )
    
    discount3 = fields.Float(
        string='Desc. 3 (%)',
        digits='Discount',
        default=0.0,
        help="Tercer descuento en cascada aplicado al precio del proveedor."
    )
    
    discount4 = fields.Float(
        string='Desc. 4 (%)',
        digits='Discount',
        default=0.0,
        help="Cuarto descuento en cascada aplicado al precio del proveedor."
    )
    
    # Campo computado para mostrar el precio final con todos los descuentos
    final_price = fields.Float(
        string='Precio Final',
        compute='_compute_final_price',
        digits='Product Price',
        help="Precio final después de aplicar todos los descuentos en cascada."
    )
    
    @api.depends('price', 'discount1', 'discount2', 'discount3', 'discount4')
    def _compute_final_price(self):
        """Calcula el precio final aplicando todos los descuentos en cascada"""
        for record in self:
            price = record.price or 0.0
            discounts = [
                record.discount1 or 0.0,
                record.discount2 or 0.0,
                record.discount3 or 0.0,
                record.discount4 or 0.0
            ]
            
            final_price = price
            for disc in discounts:
                if disc > 0:
                    final_price *= (1 - (disc / 100.0))
            
            record.final_price = final_price
    
    @api.constrains('discount1', 'discount2', 'discount3', 'discount4')
    def _check_discount_values(self):
        """Valida que los descuentos estén en un rango válido (0-100)"""
        for record in self:
            discounts = [record.discount1, record.discount2, record.discount3, record.discount4]
            for disc in discounts:
                if disc and (disc < 0 or disc > 100):
                    raise ValidationError(_('Los descuentos deben estar entre 0 y 100%'))