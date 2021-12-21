from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_length = fields.Float("Length")
    product_width = fields.Float("Width")
    product_height = fields.Float("Height")
    dimensional_uom_id = fields.Many2one('uom.uom', "Dimensional UoM", required=True,
                                         default=lambda self: self.product_tmpl_id._get_length_uom_id_from_ir_config_parameter().id,
                                         domain=lambda self: [("category_id", "=", self.env.ref("uom.uom_categ_length").id)],
                                         help="UoM for length, height, width")

    product_length_m = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)
    product_width_m = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)
    product_height_m = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)
    product_dimension_max_m = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)

    volume = fields.Float(compute='_compute_product_dimensions', store=True, compute_sudo=True)

    weight_user_uom_id = fields.Many2one('uom.uom', "Weight UoM", default=lambda self: self.product_tmpl_id._get_weight_uom_id_from_ir_config_parameter().id,
                                         domain=lambda self: [("category_id", "=", self.env.ref("uom.product_uom_categ_kgm").id)], required=True)
    weight_user = fields.Float("Weight")
    weight = fields.Float("Internal Weight", compute='_compute_product_dimensions', store=True, compute_sudo=True)

    @api.depends('product_length', 'product_width', 'product_height', 'dimensional_uom_id', 'weight_user', 'weight_user_uom_id')
    def _compute_product_dimensions(self):
        uom_weight_config = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        uom_volume_config = self.env['product.template']._get_volume_uom_id_from_ir_config_parameter()
        uom_volume_meter = self.env.ref('uom.product_uom_cubic_meter')
        uom_meter = self.env.ref('uom.product_uom_meter')
        for product in self:
            product.product_length_m = product.dimensional_uom_id._compute_quantity(product.product_length, uom_meter)
            product.product_width_m = product.dimensional_uom_id._compute_quantity(product.product_width, uom_meter)
            product.product_height_m = product.dimensional_uom_id._compute_quantity(product.product_height, uom_meter)
            product.product_dimension_max_m = max(product.product_length_m, product.product_width_m, product.product_height_m)

            volume = product.product_length_m * product.product_width_m * product.product_height_m
            product.volume = uom_volume_meter._compute_quantity(volume, uom_volume_config)

            product.weight = product.weight_user_uom_id._compute_quantity(product.weight_user, uom_weight_config)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_length = fields.Float(related="product_variant_ids.product_length", readonly=False, store=True)
    product_width = fields.Float(related="product_variant_ids.product_width", readonly=False, store=True)
    product_height = fields.Float(related="product_variant_ids.product_height", readonly=False, store=True)
    dimensional_uom_id = fields.Many2one(related="product_variant_ids.dimensional_uom_id", readonly=False, required=True,
                                         default=lambda self: self._get_length_uom_id_from_ir_config_parameter().id)

    weight_user_uom_id = fields.Many2one(related="product_variant_ids.weight_user_uom_id", readonly=False, required=True,
                                         default=lambda self: self._get_weight_uom_id_from_ir_config_parameter().id)
    weight_user = fields.Float(related="product_variant_ids.weight_user", readonly=False)
    weight = fields.Float("Internal Weight", readonly=True)
    volume = fields.Float(readonly=True)

    @api.model
    def _initialize_weight_user(self):
        """ Called after module installation """

        for product_id in self.search([('weight', '!=', 0)]):
            product_id.weight_user = product_id.weight

    def action_edit_dimension_multi(self):
        return {
            'name': "Bulk Edit Dimensions",
            'view_mode': 'form',
            'res_model': 'product.dimension.edit',
            'context': {
                'default_product_template_ids': self.ids,
                'default_dimensional_uom_id': self[0].dimensional_uom_id.id,
                'default_weight_user_uom_id': self[0].weight_user_uom_id.id,
            },
            'type': 'ir.actions.act_window',
            'target': 'new'
        }


class ProductDimension(models.TransientModel):
    _name = 'product.dimension.edit'
    _description = 'Product Dimensions'

    product_template_ids = fields.Many2many('product.template', required=True)

    product_length = fields.Float(related="product_template_ids.product_length", readonly=False, store=True)
    product_width = fields.Float(related="product_template_ids.product_width", readonly=False, store=True)
    product_height = fields.Float(related="product_template_ids.product_height", readonly=False, store=True)
    dimensional_uom_id = fields.Many2one(related="product_template_ids.dimensional_uom_id", readonly=False, required=True,
                                         default=lambda self: self.product_template_ids._get_length_uom_id_from_ir_config_parameter().id)

    weight_user = fields.Float(related="product_template_ids.weight_user", readonly=False)
    weight_user_uom_id = fields.Many2one(related="product_template_ids.weight_user_uom_id", readonly=False, required=True,
                                         default=lambda self: self.product_template_ids._get_weight_uom_id_from_ir_config_parameter().id)

    def action_save(self):
        self.product_template_ids.write({
            'product_length': self.product_length,
            'product_width': self.product_width,
            'product_height': self.product_height,
            'dimensional_uom_id': self.dimensional_uom_id.id,
            'weight_user': self.weight_user,
            'weight_user_uom_id': self.weight_user_uom_id.id,
        })
