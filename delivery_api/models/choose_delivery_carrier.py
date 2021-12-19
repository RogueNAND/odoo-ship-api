from odoo import api, models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    @api.onchange('carrier_id')
    def _onchange_carrier_id(self):
        self.delivery_message = False
        if self.carrier_id:
            vals = self._get_shipment_rate()
            if vals.get('error_message'):
                return {'warning': {
                    'title': 'Error',
                    'message': vals['error_message']}
                }
