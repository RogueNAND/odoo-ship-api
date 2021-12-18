from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    address_verify_ship_api_id = fields.Many2one('delivery.carrier.api', string="Shipping API for Partner Address Verification",
                                                 domain=[('supports_address_validation', '=', True)])
