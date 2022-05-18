from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def shipengine_get_address(self):
        self.ensure_one()

        residential = "unknown" if self.ship_address_dirty\
            else "yes" if self.address_indicator == 'residential'\
            else "no" if self.address_indicator == 'commercial'\
            else "unknown"

        parent = self.parent_id
        company = self.commercial_partner_id
        return {
            "name": self.display_name or "",
            "phone": self.phone or self.mobile or parent.phone or parent.mobile or company.phone or company.mobile or "",
            "email": self.email or parent.email or company.email or "",
            "company_name": self.commercial_company_name or parent.name or "",
            "address_line1": self.street or "",
            "address_line2": self.street2 or "",
            "address_line3": "",
            "city_locality": self.city or "",
            "state_province": self.state_id.code or "",
            "postal_code": self.zip or "",
            "country_code": self.country_id.code or "",
            "address_residential_indicator": residential
        }
