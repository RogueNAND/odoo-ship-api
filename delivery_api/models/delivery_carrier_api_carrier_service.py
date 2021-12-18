from odoo import fields, models


class DeliveryCarrierApiCarrierService(models.Model):
    _name = 'delivery.carrier.api.carrier.service'
    _description = 'API Carrier Service'

    delivery_api_id = fields.Many2one(related='api_carrier_id.delivery_api_id', store=True)
    api_carrier_id = fields.Many2one('delivery.carrier.api.carrier', string="Carrier", required=True, ondelete='cascade')
    name = fields.Char(required=True)
    code = fields.Char(required=True)

    _sql_constraints = [('code_api_unique', 'unique(code, api_carrier_id)', 'Programming error: API Carrier Service already exists')]
