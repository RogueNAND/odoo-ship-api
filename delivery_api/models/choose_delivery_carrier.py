from odoo import api, fields, models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    package_description = fields.Char(compute='_compute_package_description')

    @api.depends('order_id.order_line')
    def _compute_package_description(self):
        for choose in self:
            package_id, l, w, h, weight = choose.order_id.order_line.estimate_package()

            from_dim_uom = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()
            from_weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
            to_dim_uom = self.env['product.template']._get_default_dimension_user_uom_id()
            to_weight_uom = self.env['product.template']._get_default_weight_user_uom_id()

            l = from_dim_uom._compute_quantity(l, to_dim_uom)
            w = from_dim_uom._compute_quantity(w, to_dim_uom)
            h = from_dim_uom._compute_quantity(h, to_dim_uom)
            weight = from_weight_uom._compute_quantity(weight, to_weight_uom)

            choose.package_description = f"<strong>Estimated Package Dimensions:</strong><br/>" \
                                         f"<b>{l:0.1f}</b> x <b>{w:0.1f}</b> x <b>{h:0.1f}</b>{to_dim_uom.name}, <b>{weight:0.1f}</b>{to_weight_uom.name}"

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
