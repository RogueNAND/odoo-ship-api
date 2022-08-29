from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    package_carrier_type = fields.Selection(selection_add=[('ship_api', 'Shipping API')], ondelete={'ship_api': 'set default'})
    freight_package_type = fields.Selection([
        ('box', "Box"),
        ('crate', "Crate"),
        ('pallet', "Pallet"),
        ('conex', "Conex")
    ], string="Freight Package")
    height = fields.Float()
    variable_dimensions = fields.Boolean(string="Variable Height")
    min_height = fields.Float("Minimum Height")
    width = fields.Float()
    packaging_length = fields.Float()
    volume = fields.Float(compute='_compute_volume', store=True)
    dimension_max = fields.Float(compute='_compute_dimension_max', store=True)

    @api.model
    def _rewrite_package_lwh(self):
        """
        When the 'delivery' module updates, all lwh are reset.
        This reloads the values after a module update.
        """
        lwh_map = self.env['ir.config_parameter'].sudo().get_param('delivery_api.delivery_api_package_dimensions')
        if lwh_map:
            lwh_map = json.loads(lwh_map)
            for p_id, (l, w, h) in lwh_map.items():
                p = self.browse(int(p_id))
                if p.exists() and p.packaging_length == p.width == p.height == 0:
                    p.write({
                        'packaging_length': l,
                        'width': w,
                        'height': h
                    })

    @api.constrains('variable_dimensions', 'min_height', 'height')
    def _constrain_min_dimensions(self):
        for packaging in self.filtered(lambda x: x.package_carrier_type == 'ship_api' and x.variable_dimensions):
            if packaging.min_height >= packaging.height:
                raise ValidationError(_("Minimum dimension must be less than Maximum dimension"))

    @api.constrains('package_carrier_type', 'height', 'width', 'packaging_length')
    def _constrain_dimensions(self):
        error_packages = self.filtered(lambda x: x.package_carrier_type == 'ship_api' and not (x.height and x.width and x.packaging_length))
        if error_packages:
            raise ValidationError(_("Package must have Height, Width, and Length"))

    @api.depends('height', 'width', 'packaging_length')
    def _compute_dimension_max(self):
        for packaging in self:
            packaging.dimension_max = max(packaging.height, packaging.width, packaging.packaging_length)

    @api.depends('height', 'width', 'packaging_length')
    def _compute_volume(self):
        for packaging in self:
            packaging.volume = packaging.height * packaging.width * packaging.packaging_length

    def write(self, vals):
        """ Ensure sale.order.line estimate_package() does not pull from cache if any packages are changed """

        res = super(ProductPackaging, self).write(vals)
        if any(f in vals for f in ['packaging_length', 'width', 'height', 'variable_dimensions', 'min_height', 'max_weight']):
            self.env['sale.order.line'].clear_caches()

        if any(f in vals for f in ['packaging_length', 'width', 'height']):
            # Save lwh values in case of 'delivery' module update
            lwh_map = {
                p.id: (p.packaging_length, p.width, p.height)
                for p in self.search([('package_carrier_type', '=', 'ship_api')])
            }
            self.env['ir.config_parameter'].sudo().set_param('delivery_api.delivery_api_package_dimensions', json.dumps(lwh_map))
        return res

    _sql_constraints = [
        ('positive_min_height', 'CHECK(min_height>=0)', 'Minimum Height must be positive'),
    ]
