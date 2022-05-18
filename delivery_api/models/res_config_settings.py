from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    address_verify_ship_api_id = fields.Many2one(related='company_id.address_verify_ship_api_id', readonly=False)
    product_weight_uom_id = fields.Many2one('uom.uom', domain=lambda self: [("category_id", "=", self.env.ref("uom.product_uom_categ_kgm").id)],
                                            string="Default Weight UoM",
                                            config_parameter='product.default_weight_uom_id')
    product_dimension_uom_id = fields.Many2one('uom.uom', domain=lambda self: [("category_id", "=", self.env.ref("uom.uom_categ_length").id)],
                                               string="Default Dimension UoM",
                                               config_parameter='product.default_dimension_uom_id')
    delivery_default_freight_code = fields.Many2one('delivery.freight.code', string="Fallback freight class when none exists",
                                                    config_parameter='delivery.default_freight_code')
