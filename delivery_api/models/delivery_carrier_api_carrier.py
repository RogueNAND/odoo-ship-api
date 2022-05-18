from odoo import fields, models


class DeliveryCarrierApiCarrier(models.Model):
    _name = 'delivery.carrier.api.carrier'
    _description = 'API Carrier'

    code = fields.Char(required=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    usable = fields.Boolean(help="Allows this carrier to be shown or hidden when creating a shipping method")
    freight_type = fields.Selection([
        ('ltl', "Less Than Truckload"),
        ('ftl', "Full Truckload")
    ], readonly=True)
    delivery_api = fields.Selection(related='delivery_api_id.delivery_api', string="API")
    delivery_api_id = fields.Many2one('delivery.carrier.api', required=True, ondelete='cascade', readonly=True)
    service_ids = fields.One2many('delivery.carrier.api.carrier.service', 'api_carrier_id', readonly=True)

    _sql_constraints = [('code_api_unique', 'unique(code)', 'Programming error: API Carrier already exists')]

    def sync_services(self, services):
        """ Ensure all carrier accounts and services are loaded from api """

        self.ensure_one()

        service_ids = self.env['delivery.carrier.api.carrier.service']
        for service in services:
            service_id = self.env['delivery.carrier.api.carrier.service'].search([
                ('api_carrier_id', '=', self.id),
                ('code', '=', service['code'])
            ]) or self.env['delivery.carrier.api.carrier.service'].create({'api_carrier_id': self.id, **service})
            service_id.write(service)
            service_ids |= service_id

        services_to_delete = self.env['delivery.carrier.api.carrier.service'].search([('api_carrier_id', '=', self.id)]) - service_ids
        services_to_delete.unlink()
