from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_length = fields.Float("Length")
    product_width = fields.Float("Width")
    product_height = fields.Float("Height")
    dimensional_uom_id = fields.Many2one('uom.uom', "Dimensional UoM", required=True,
                                         default=lambda self: self.product_tmpl_id._get_default_dimension_user_uom_id().id,
                                         domain=lambda self: [("category_id", "=", self.env.ref("uom.uom_categ_length").id)],
                                         help="UoM for length, height, width")

    product_length_u = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)
    product_width_u = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)
    product_height_u = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)
    product_dimension_max_u = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)

    volume = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)

    weight_user_uom_id = fields.Many2one('uom.uom', "Weight UoM", default=lambda self: self.product_tmpl_id._get_default_weight_user_uom_id().id,
                                         domain=lambda self: [("category_id", "=", self.env.ref("uom.product_uom_categ_kgm").id)], required=True)
    weight_user = fields.Float("Weight")
    weight = fields.Float("Internal Weight", compute='_compute_product_dimensions', store=True, compute_sudo=True)

    freight_code = fields.Many2one('delivery.freight.code', string="Freight Class")

    shipping_hazardous = fields.Boolean("Hazardous", help="Examples include:\n\n"
                                                          "Lithium-ion batteries\n"
                                                          "Aerosols, compressed gases, or other pressurized containers\n"
                                                          "Dry ice\n"
                                                          "Flammable liquids\n"
                                                          "Poisons\n"
                                                          "Some fertilizers")
    shipping_perishable = fields.Boolean("Perishable", help="Note: the use of dry ice also considered Hazardous!")

    @api.depends('product_length', 'product_width', 'product_height', 'dimensional_uom_id', 'weight_user', 'weight_user_uom_id')
    def _compute_product_dimensions(self):
        uom_length_config = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()
        uom_weight_config = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for product in self:
            product.product_length_u = product.dimensional_uom_id._compute_quantity(product.product_length, uom_length_config)
            product.product_width_u = product.dimensional_uom_id._compute_quantity(product.product_width, uom_length_config)
            product.product_height_u = product.dimensional_uom_id._compute_quantity(product.product_height, uom_length_config)
            product.product_dimension_max_u = max(product.product_length_u, product.product_width_u, product.product_height_u)
            product.volume = product.product_length_u * product.product_width_u * product.product_height_u
            product.weight = product.weight_user_uom_id._compute_quantity(product.weight_user, uom_weight_config)

    def action_edit_dimension_multi(self):
        return {
            'name': "Bulk Edit Dimensions",
            'view_mode': 'form',
            'res_model': 'product.dimension.edit',
            'context': {
                'default_product_ids': self.ids,
                'default_dimensional_uom_id': self[0].dimensional_uom_id.id,
                'default_weight_user_uom_id': self[0].weight_user_uom_id.id,
            },
            'type': 'ir.actions.act_window',
            'target': 'new'
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_length = fields.Float(related="product_variant_ids.product_length", readonly=False, store=True)
    product_width = fields.Float(related="product_variant_ids.product_width", readonly=False, store=True)
    product_height = fields.Float(related="product_variant_ids.product_height", readonly=False, store=True)
    dimensional_uom_id = fields.Many2one(related="product_variant_ids.dimensional_uom_id", readonly=False, required=True,
                                         default=lambda self: self._get_default_dimension_user_uom_id().id)

    weight_user_uom_id = fields.Many2one(related="product_variant_ids.weight_user_uom_id", readonly=False, required=True,
                                         default=lambda self: self._get_default_weight_user_uom_id().id)
    weight_user = fields.Float(related="product_variant_ids.weight_user", readonly=False)
    weight = fields.Float("Internal Weight", readonly=True)
    volume = fields.Float(readonly=True)

    freight_code = fields.Many2one(related="product_variant_ids.freight_code", readonly=False, store=True)

    shipping_hazardous = fields.Boolean(related='product_variant_ids.shipping_hazardous', readonly=False, store=True)
    shipping_perishable = fields.Boolean(related='product_variant_ids.shipping_perishable', readonly=False, store=True)

    @api.model
    def _initialize_weight_user(self):
        """ Called after module installation """

        for product_id in self.search([('weight', '!=', 0)]):
            product_id.weight_user = product_id.weight

    @api.model
    def _get_default_dimension_user_uom_id(self):
        default_dimension_uom_id = self.env['ir.config_parameter'].sudo().get_param('product.default_dimension_uom_id')
        default_dimension_uom_id = self.env['uom.uom'].browse(default_dimension_uom_id and int(default_dimension_uom_id))
        return default_dimension_uom_id or self._get_length_uom_id_from_ir_config_parameter()

    @api.model
    def _get_default_weight_user_uom_id(self):
        default_weight_uom_id = self.env['ir.config_parameter'].sudo().get_param('product.default_weight_uom_id')
        default_weight_uom_id = self.env['uom.uom'].browse(default_weight_uom_id and int(default_weight_uom_id))
        return default_weight_uom_id or self._get_weight_uom_id_from_ir_config_parameter()


class ProductDimension(models.TransientModel):
    _name = 'product.dimension.edit'
    _description = 'Product Dimensions'

    product_ids = fields.Many2many('product.product', required=True)

    product_length = fields.Float(related="product_ids.product_length", readonly=False, store=True)
    product_width = fields.Float(related="product_ids.product_width", readonly=False, store=True)
    product_height = fields.Float(related="product_ids.product_height", readonly=False, store=True)
    dimensional_uom_id = fields.Many2one(related="product_ids.dimensional_uom_id", readonly=False, required=True,
                                         default=lambda self: self.product_ids.product_tmpl_id._get_default_dimension_user_uom_id().id)

    weight_user = fields.Float(related="product_ids.weight_user", readonly=False)
    weight_user_uom_id = fields.Many2one(related="product_ids.weight_user_uom_id", readonly=False, required=True,
                                         default=lambda self: self.product_ids.product_tmpl_id._get_default_weight_user_uom_id().id)

    freight_code = fields.Many2one(related="product_ids.freight_code", readonly=False,
                                   default=lambda self: self.product_ids.freight_code.get_maximum().id)

    shipping_hazardous = fields.Boolean(related='product_ids.shipping_hazardous', readonly=False)
    shipping_perishable = fields.Boolean(related='product_ids.shipping_perishable', readonly=False)

    def action_save(self):
        self.product_ids.write({
            'product_length': self.product_length,
            'product_width': self.product_width,
            'product_height': self.product_height,
            'dimensional_uom_id': self.dimensional_uom_id.id,
            'weight_user': self.weight_user,
            'weight_user_uom_id': self.weight_user_uom_id.id,
            'freight_code': self.freight_code.id,
            'shipping_hazardous': self.shipping_hazardous,
            'shipping_perishable': self.shipping_perishable,
        })
