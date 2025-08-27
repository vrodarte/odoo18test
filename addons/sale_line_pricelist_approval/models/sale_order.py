# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    state = fields.Selection(
        selection_add=[
            ('to_approve', 'Esperando Aprobación'),
        ],
        ondelete={'to_approve': 'set default'}
    )
    
    has_pending_approval = fields.Boolean(
        string="Tiene líneas pendientes de aprobación",
        compute='_compute_has_pending_approval',
        store=True
    )
    
    can_approve = fields.Boolean(
        string="Puede aprobar",
        compute='_compute_can_approve'
    )
    
    @api.depends('order_line.x_approval_status')
    def _compute_has_pending_approval(self):
        for order in self:
            order.has_pending_approval = any(
                line.x_approval_status == 'pending' for line in order.order_line
            )
    
    @api.depends('state')
    def _compute_can_approve(self):
        for order in self:
            order.can_approve = self.env.user.has_group('sale_line_pricelist_approval.group_sale_price_approver')
    
    def action_confirm(self):
        """Sobrescribe el método de confirmación para verificar aprobaciones"""
        for order in self:
            pending_lines = order.order_line.filtered(
                lambda l: l.x_approval_status == 'pending'
            )
            if pending_lines:
                line_names = ', '.join(pending_lines.mapped('name')[:3])
                if len(pending_lines) > 3:
                    line_names += f' y {len(pending_lines) - 3} más'
                raise UserError(_(
                    'No se puede confirmar la orden.\n\n'
                    'Las siguientes líneas tienen precios manuales pendientes de aprobación:\n'
                    '%s\n\n'
                    'Por favor, solicite aprobación antes de confirmar.'
                ) % line_names)
            
            rejected_lines = order.order_line.filtered(
                lambda l: l.x_approval_status == 'rejected'
            )
            if rejected_lines:
                raise UserError(_(
                    'No se puede confirmar la orden.\n'
                    'Existen líneas con precios rechazados. '
                    'Por favor, corrija los precios antes de continuar.'
                ))
        
        return super().action_confirm()
    
    def action_request_approval(self):
        """Solicita aprobación para líneas con precios manuales"""
        self.ensure_one()
        
        if not self.has_pending_approval:
            raise UserError(_('No hay líneas pendientes de aprobación.'))
        
        # Cambiar estado a esperando aprobación
        self.state = 'to_approve'
        
        # Buscar aprobadores
        approvers = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('sale_line_pricelist_approval.group_sale_price_approver').id)
        ])
        
        if not approvers:
            raise UserError(_('No se encontraron aprobadores configurados en el sistema.'))
        
        # Preparar detalles de las líneas pendientes
        pending_lines = self.order_line.filtered(lambda l: l.x_approval_status == 'pending')
        lines_detail = '<ul>'
        total_manual = 0.0
        
        for line in pending_lines:
            lines_detail += f'<li><b>{line.product_id.name}</b>: '
            lines_detail += f'{line.product_uom_qty} {line.product_uom.name} '
            lines_detail += f'@ {line.price_unit:.2f} {self.currency_id.symbol} '
            lines_detail += f'(Subtotal: {line.price_subtotal:.2f} {self.currency_id.symbol})</li>'
            total_manual += line.price_subtotal
        
        lines_detail += '</ul>'
        
        # Crear mensaje en el chatter
        message_body = f"""
        <p><b>🔔 Solicitud de Aprobación de Precios Especiales</b></p>
        <p>El usuario <b>{self.env.user.name}</b> ha solicitado aprobación para las siguientes líneas con precios manuales:</p>
        {lines_detail}
        <p><b>Total de líneas con precio manual:</b> {total_manual:.2f} {self.currency_id.symbol}</p>
        <p><b>Total de la orden:</b> {self.amount_total:.2f} {self.currency_id.symbol}</p>
        <br/>
        <p>Por favor, revise y apruebe o rechace los precios especiales.</p>
        """
        
        # Mencionar a los aprobadores
        partner_ids = approvers.mapped('partner_id').ids
        
        self.message_post(
            body=message_body,
            subject=f'Aprobación requerida - {self.name}',
            partner_ids=partner_ids,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Solicitud Enviada'),
                'message': _('Se ha enviado la solicitud de aprobación a los gerentes.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_approve_prices(self):
        """Aprueba todos los precios manuales pendientes"""
        self.ensure_one()
        
        if not self.can_approve:
            raise UserError(_('No tiene permisos para aprobar precios especiales.'))
        
        pending_lines = self.order_line.filtered(lambda l: l.x_approval_status == 'pending')
        
        if not pending_lines:
            raise UserError(_('No hay líneas pendientes de aprobación.'))
        
        # Aprobar todas las líneas pendientes
        pending_lines.write({
            'x_approval_status': 'approved',
            'x_approved_by': self.env.user.id,
            'x_approval_date': fields.Datetime.now(),
        })
        
        # Cambiar estado si corresponde
        if self.state == 'to_approve':
            self.state = 'draft'
        
        # Registrar en el chatter
        lines_approved = '<ul>'
        for line in pending_lines:
            lines_approved += f'<li>{line.product_id.name}: {line.price_unit:.2f} {self.currency_id.symbol}</li>'
        lines_approved += '</ul>'
        
        self.message_post(
            body=f"""
            <p><b>✅ Precios Especiales Aprobados</b></p>
            <p>El usuario <b>{self.env.user.name}</b> ha aprobado los siguientes precios especiales:</p>
            {lines_approved}
            <p>La orden ahora puede ser confirmada.</p>
            """,
            subject=f'Precios aprobados - {self.name}',
            message_type='notification',
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Precios Aprobados'),
                'message': _('Los precios especiales han sido aprobados exitosamente.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_reject_prices(self):
        """Rechaza todos los precios manuales pendientes"""
        self.ensure_one()
        
        if not self.can_approve:
            raise UserError(_('No tiene permisos para rechazar precios especiales.'))
        
        pending_lines = self.order_line.filtered(lambda l: l.x_approval_status == 'pending')
        
        if not pending_lines:
            raise UserError(_('No hay líneas pendientes para rechazar.'))
        
        # Rechazar todas las líneas pendientes
        pending_lines.write({
            'x_approval_status': 'rejected',
            'x_approved_by': self.env.user.id,
            'x_approval_date': fields.Datetime.now(),
        })
        
        # Cambiar estado si corresponde
        if self.state == 'to_approve':
            self.state = 'draft'
        
        # Registrar en el chatter
        self.message_post(
            body=f"""
            <p><b>❌ Precios Especiales Rechazados</b></p>
            <p>El usuario <b>{self.env.user.name}</b> ha rechazado los precios especiales.</p>
            <p>Por favor, revise y corrija los precios antes de volver a solicitar aprobación.</p>
            """,
            subject=f'Precios rechazados - {self.name}',
            message_type='notification',
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Precios Rechazados'),
                'message': _('Los precios especiales han sido rechazados.'),
                'type': 'warning',
                'sticky': False,
            }
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    x_pricing_choice = fields.Selection(
        [
            ('pricelist', 'Lista de Precios'),
            ('manual', 'Precio Manual')
        ],
        string='Tipo de Precio',
        default='pricelist',
        required=True,
        help='Seleccione entre usar una lista de precios predefinida o establecer un precio manual'
    )
    
    x_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de Precios',
        domain="[('x_is_line_pricelist', '=', True)]",
        help='Seleccione una de las listas de precios disponibles'
    )
    
    x_approval_status = fields.Selection(
        [
            ('na', 'No Aplica'),
            ('pending', 'Pendiente'),
            ('approved', 'Aprobado'),
            ('rejected', 'Rechazado')
        ],
        string='Estado de Aprobación',
        default='na',
        required=True,
        help='Estado de aprobación para precios manuales'
    )
    
    x_approved_by = fields.Many2one(
        'res.users',
        string='Aprobado por',
        readonly=True
    )
    
    x_approval_date = fields.Datetime(
        string='Fecha de Aprobación',
        readonly=True
    )
    
    x_original_price = fields.Float(
        string='Precio Original',
        digits='Product Price',
        help='Precio calculado según lista de precios estándar'
    )
    
    @api.onchange('x_pricing_choice', 'x_pricelist_id', 'product_id', 'product_uom_qty')
    def _onchange_pricing_fields(self):
        """Maneja los cambios en los campos de precio"""
        if not self.product_id:
            return
        
        if self.x_pricing_choice == 'pricelist':
            if self.x_pricelist_id:
                # Obtener precio de la lista seleccionada
                price = self.x_pricelist_id._get_product_price(
                    self.product_id,
                    self.product_uom_qty or 1.0,
                    uom=self.product_uom,
                    date=self.order_id.date_order,
                    currency=self.order_id.currency_id
                )
                self.price_unit = price
                self.x_approval_status = 'na'
                self.x_original_price = price
            else:
                # Usar lista de precios de la orden
                if self.order_id.pricelist_id:
                    self._compute_price_unit()
                    self.x_approval_status = 'na'
                    self.x_original_price = self.price_unit
        
        elif self.x_pricing_choice == 'manual':
            # Precio manual requiere aprobación
            self.x_pricelist_id = False
            self.x_approval_status = 'pending'
            # Guardar el precio original para referencia
            if not self.x_original_price and self.order_id.pricelist_id:
                original_price = self.order_id.pricelist_id._get_product_price(
                    self.product_id,
                    self.product_uom_qty or 1.0,
                    uom=self.product_uom,
                    date=self.order_id.date_order,
                    currency=self.order_id.currency_id
                )
                self.x_original_price = original_price
    
    @api.constrains('price_unit', 'x_pricing_choice', 'x_original_price')
    def _check_manual_price_variation(self):
        """Valida que el precio manual no exceda límites configurables"""
        for line in self:
            if line.x_pricing_choice == 'manual' and line.x_original_price > 0:
                # Calcular variación porcentual
                variation = abs((line.price_unit - line.x_original_price) / line.x_original_price * 100)
                
                # Límite configurable (por defecto 50%)
                max_variation = self.env['ir.config_parameter'].sudo().get_param(
                    'sale_line_pricelist_approval.max_price_variation', 
                    default='50'
                )
                
                try:
                    max_variation = float(max_variation)
                except ValueError:
                    max_variation = 50.0
                
                if variation > max_variation:
                    raise ValidationError(_(
                        'El precio manual no puede variar más del %.0f%% del precio original.\n'
                        'Precio original: %.2f\n'
                        'Precio manual: %.2f\n'
                        'Variación: %.2f%%'
                    ) % (max_variation, line.x_original_price, line.price_unit, variation))
    
    def write(self, vals):
        """Intercepta cambios para manejar el estado de aprobación"""
        if 'price_unit' in vals and self.x_pricing_choice == 'manual':
            # Si cambia el precio manual y ya estaba aprobado, vuelve a pendiente
            for line in self:
                if line.x_approval_status == 'approved':
                    vals['x_approval_status'] = 'pending'
                    vals['x_approved_by'] = False
                    vals['x_approval_date'] = False
        
        return super().write(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Asegura valores correctos al crear líneas"""
        for vals in vals_list:
            if vals.get('x_pricing_choice') == 'manual':
                vals['x_approval_status'] = 'pending'
            elif 'x_pricing_choice' not in vals:
                vals['x_pricing_choice'] = 'pricelist'
                vals['x_approval_status'] = 'na'
        
        return super().create(vals_list)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    
    x_is_line_pricelist = fields.Boolean(
        string='Disponible para líneas de venta',
        default=False,
        help='Marcar si esta lista de precios debe estar disponible para selección en líneas de pedido'
    )