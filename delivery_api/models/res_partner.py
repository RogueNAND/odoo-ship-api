from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    address_indicator = fields.Selection([('residential', "🏠 Residential"), ('commercial', "🏢 Commercial")], readonly=True)
    ship_stored_hash = fields.Char(readonly=True)
    ship_live_hash = fields.Char(compute='_compute_ship_address_dirty', store=True)
    ship_address_dirty = fields.Boolean(compute='_compute_ship_address_dirty', store=True)

    @api.model
    def get_address_hash(self, street: str, street2: str, city: str, state_id: int, zip: str, country_id: int, address_indicator):
        return hash((
            street or False,
            street2 or False,
            city or False,
            int(state_id or False),
            zip or False,
            int(country_id or False),
            address_indicator or False
        ))

    @api.depends('street', 'street2', 'city', 'state_id', 'zip', 'country_id', 'address_indicator', 'ship_stored_hash')
    def _compute_ship_address_dirty(self):
        """ Has the address changed since the last verification? """

        for partner_id in self:
            partner_id.ship_live_hash = self.get_address_hash(
                partner_id.street,
                partner_id.street2,
                partner_id.city,
                partner_id.state_id.id,
                partner_id.zip,
                partner_id.country_id.id,
                partner_id.address_indicator
            )
            partner_id.ship_address_dirty = partner_id.ship_stored_hash != partner_id.ship_live_hash

    def action_verify_ship_address(self):
        self.ensure_one()

        ship_api_id = self.env.user.company_id.address_verify_ship_api_id
        if ship_api_id:
            success, message, user_confirm, data = ship_api_id._verify_address(
                self.name,
                self.commercial_partner_id.name,
                self.phone or self.mobile
                or self.parent_id.phone or self.parent_id.mobile
                or self.commercial_partner_id.phone or self.commercial_partner_id.mobile,
                self.street,
                self.street2,
                self.city,
                self.state_id.code,
                self.zip,
                self.country_id.code
            )
            if success:
                if user_confirm:
                    data.update({'partner_id': self.id, 'message': message})
                    return {
                        'name': "Verify Address",
                        'view_mode': 'form',
                        'res_model': 'res.partner.verify',
                        'res_id': self.env['res.partner.verify'].create(data).id,
                        'type': 'ir.actions.act_window',
                        'target': 'new'
                    }
                else:
                    self.write(data)
                    self.ship_stored_hash = self.ship_live_hash
            else:
                raise UserError(_("Could not verify the shipping address. Please double check it carefully.\n\n%s") % message)
        else:
            raise UserError(_("Odoo has not been setup for address verification yet.\nPlease select the shipping api to use for address verification in settings."))
