from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartnerVerify(models.TransientModel):
    _name = 'res.partner.verify'
    _description = 'Contact Address Verification'

    partner_id = fields.Many2one('res.partner', required=True)
    message = fields.Text()

    origin_street = fields.Char(related='partner_id.street', string="Origin Street")
    origin_street2 = fields.Char(related='partner_id.street2', string="Origin Street 2")
    origin_city = fields.Char(related='partner_id.city', string="Origin City")
    origin_state_id = fields.Many2one(related='partner_id.state_id', string="Origin State")
    origin_zip = fields.Char(related='partner_id.zip', string="Origin Zip")
    origin_country_id = fields.Many2one(related='partner_id.country_id', string="Origin Country")

    street = fields.Char(readonly=True)
    street2 = fields.Char(readonly=True)
    city = fields.Char(readonly=True)
    zip = fields.Char(readonly=True)
    address_indicator = fields.Selection([('residential', "🏠 Residential"), ('commercial', "🏢 Commercial")], readonly=True)
    state_id = fields.Many2one('res.country.state', readonly=True)
    country_id = fields.Many2one(related='state_id.country_id')

    diff_street = fields.Boolean(compute='_compute_diffs')
    diff_street2 = fields.Boolean(compute='_compute_diffs')
    diff_city = fields.Boolean(compute='_compute_diffs')
    diff_state = fields.Boolean(compute='_compute_diffs')
    diff_zip = fields.Boolean(compute='_compute_diffs')
    diff_country = fields.Boolean(compute='_compute_diffs')

    @api.depends('partner_id')
    def _compute_diffs(self):
        for r in self:
            p = r.partner_id
            diffs = self.env['delivery.carrier.api'].compare_address_diff(
                p.street, p.street2, p.city, p.state_id.code, p.zip, p.country_id.code,
                r.street, r.street2, r.city, r.state_id.code, r.zip, r.country_id.code
            )
            r.diff_street = 'street' in diffs
            r.diff_street2 = 'street2' in diffs
            r.diff_city = 'city' in diffs
            r.diff_state = 'state' in diffs
            r.diff_zip = 'zip' in diffs
            r.diff_country = 'country' in diffs

    def action_update_partner_address(self):
        self.partner_id.write({
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
            'address_indicator': self.address_indicator,
        })
        self.partner_id.ship_stored_hash = self.partner_id.ship_live_hash
