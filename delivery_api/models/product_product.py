from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_length_m = fields.Float(compute='_compute_product_dimension_m', store=True, compute_sudo=True)
    product_width_m = fields.Float(compute='_compute_product_dimension_m', store=True, compute_sudo=True)
    product_height_m = fields.Float(compute='_compute_product_dimension_m', store=True, compute_sudo=True)
    product_dimension_max_m = fields.Float(compute='_compute_product_dimension_m', store=True, compute_sudo=True)

    @api.depends('product_length', 'product_width', 'product_height', 'dimensional_uom_id')
    def _compute_product_dimension_m(self):
        to_dimension_uom_id = self.env.ref('uom.product_uom_meter')
        for product in self:
            product.product_length_m = product.dimensional_uom_id._compute_quantity(product.product_length, to_dimension_uom_id)
            product.product_width_m = product.dimensional_uom_id._compute_quantity(product.product_width, to_dimension_uom_id)
            product.product_height_m = product.dimensional_uom_id._compute_quantity(product.product_height, to_dimension_uom_id)
            product.product_dimension_max_m = max(product.product_length_m, product.product_width_m, product.product_height_m)
