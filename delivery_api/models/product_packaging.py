from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    package_carrier_type = fields.Selection(selection_add=[('ship_api', 'Shipping API')], ondelete={'ship_api': 'set default'})
    height = fields.Float()
    variable_dimensions = fields.Boolean(string="Variable Height")
    min_height = fields.Float("Minimum Height")
    width = fields.Float()
    packaging_length = fields.Float()
    volume = fields.Float(compute='_compute_volume', store=True)
    dimension_max = fields.Float(compute='_compute_dimension_max', store=True)

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
