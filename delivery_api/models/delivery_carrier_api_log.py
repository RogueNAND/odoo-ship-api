from odoo import fields, models


class DeliveryCarrierApiLog(models.Model):
    _name = 'delivery.carrier.api.log'
    _description = 'API Carrier Log'
    _order = 'create_date DESC'

    delivery_api = fields.Many2one('delivery.carrier.api', required=True, readonly=True, ondelete='cascade')
    order_id = fields.Many2one('sale.order', "Sales Order", readonly=True)
    context = fields.Text(readonly=True)
    request = fields.Text("Request Content", readonly=True)
    response = fields.Text("Response Content", readonly=True)
