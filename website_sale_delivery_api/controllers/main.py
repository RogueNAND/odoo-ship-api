from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import logging

logger = logging.getLogger(__name__)


class WebsiteSaleShippingApi(WebsiteSale):

    def values_postprocess(self, *args, **kwargs):
        new_values, errors, error_msg = super().values_postprocess(*args, **kwargs)

        country_id = request.env['res.country'].browse(int(new_values.get('country_id')))
        state_id = request.env['res.country'].browse(int(new_values.get('state_id')))

        if country_id and state_id and not errors:
            try:
                success, message, user_confirm, data = request.env.company.address_verify_ship_api_id.sudo()._verify_address(
                    new_values.get('name'),
                    new_values.get('company_name'),
                    new_values.get('phone'),
                    new_values.get('street'),
                    new_values.get('street2'),
                    new_values.get('city'),
                    state_id.code,
                    new_values.get('zip'),
                    country_id.code
                )
                if success:
                    new_values.update(data)
                else:
                    errors['invalid_address'] = message
                    error_msg.append("Could not verify your address. Please check it carefully.")
                    error_msg += list(filter(bool, message.split('\n')))
            except Exception as e:
                logger.error("Error verifying shipping address on website (%s): %s", e, str(new_values))

        return new_values, errors, error_msg
