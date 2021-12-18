from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    address_verify_ship_api_id = fields.Many2one(related='company_id.address_verify_ship_api_id', readonly=False)
