from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeliveryFreightClass(models.Model):
    _name = 'delivery.freight.code'
    _description = 'Freight Class'
    _order = "code"

    code = fields.Float(required=True, readonly=True)
    name = fields.Char("Class", compute='_compute_name', store=True)
    description = fields.Char(required=True, help="Short descriptor to assist identifying this freight class")
    density_minimum = fields.Float("Minimum density (lb/ft)", required=True)

    @api.constrains('code')
    def _constrain_code(self):
        if self.filtered(lambda x: not (50 <= x.code <= 500)):
            raise ValidationError("Freight class must be between 50 and 500")

    @api.depends('code')
    def _compute_name(self):
        for code in self:
            if code.code == int(code.code):
                code.name = str(int(code.code))
            else:
                code.name = str(code.code).rstrip('0')

    def name_get(self):
        return [
            (code.id, f"{code.name} - {code.description}")
            for code in self
        ]

    def get_maximum(self):
        if not self:
            return self
        return self.sorted('code', reverse=True)[0]

    _sql_constraints = [('code_unique', 'unique(code)', 'Freight Class already exists')]
