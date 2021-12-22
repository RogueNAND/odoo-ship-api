from odoo import api, fields, models, _
from odoo.tools import format_amount


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('ship_api', 'Shipping API')],
                                     ondelete={'ship_api': lambda x: x.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    delivery_api_id = fields.Many2one('delivery.carrier.api')
    api_carrier_id = fields.Many2one('delivery.carrier.api.carrier', domain="[('delivery_api_id', '=', delivery_api_id), ('usable', '=', True)]")
    service_id = fields.Many2one('delivery.carrier.api.carrier.service', domain="[('api_carrier_id', '=', api_carrier_id)]")

    def name_get(self):
        """ Add pricing for sale order 'Add Shipping' wizard """

        order_id = self._context.get('estimate_order_id')
        if order_id:
            order_id = self.env['sale.order'].browse(order_id)
            currency_id = self.env['res.currency'].browse(self._context['currency_id'])
            result = []
            for carrier_id in self.sudo():
                rate = carrier_id.rate_shipment(order_id)
                if rate['success']:
                    price = rate['price']
                    if carrier_id.delivery_type == 'ship_api':
                        price = self.env.company.currency_id._convert(price, currency_id, self.env.company, fields.Date.today())
                    price = format_amount(self.env, price, currency_id)
                    error = rate['error_message']
                    text = f"{price} - {carrier_id.name}"
                    if error:
                        text += f" - {error}"
                else:
                    warning = rate['warning_message']
                    error = rate['error_message']
                    text = f"{carrier_id.name}"
                    if error:
                        text += f" - {error}"
                    if not error or warning:
                        text += " - " + _("Error retrieving shipping price")
                result.append((carrier_id.id, text))
            return result
        else:
            return super().name_get()

    @api.onchange('delivery_api_id')
    def _onchange_delivery_api_id(self):
        self.api_carrier_id = False
        self.service_id = False

    @api.onchange('api_carrier_id')
    def _onchange_delivery_api_id(self):
        self.service_id = False

    def ship_api_rate_shipment(self, order_id):
        from_partner_id = order_id.warehouse_id.partner_id or order_id.company_id.partner_id
        to_partner_id = order_id.partner_shipping_id
        service_rate_map = self.delivery_api_id.rate_estimate(from_partner_id, to_partner_id, order_id.order_line)
        rate = service_rate_map.get(self.service_id.id)
        if rate is None:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('Cannot calculate shipping price'),
                'warning_message': False
            }

        price, warning, error = rate
        return {'success': bool(not error),
                'price': self.delivery_api_id.currency_id._convert(price, self.company_id.currency_id, self.env.company, fields.Date.today()),
                'error_message': error or False,
                'warning_message': warning or False}
