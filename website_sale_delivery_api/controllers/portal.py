from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging

logger = logging.getLogger(__name__)


class PortalSaleShippingApi(CustomerPortal):

    def details_form_validate(self, data):
        error, error_message = super().details_form_validate(data)

        country_id = request.env['res.country'].browse(int(data.get('country_id')))
        state_id = request.env['res.country'].browse(int(data.get('state_id')))

        if country_id and state_id and not error:
            try:
                success, message, user_confirm, address_data = request.env.company.address_verify_ship_api_id.sudo()._verify_address(
                    data.get('name'),
                    data.get('company_name'),
                    data.get('phone'),
                    data.get('street'),
                    data.get('street2'),
                    data.get('city'),
                    state_id.code,
                    data.get('zipcode'),
                    country_id.code
                )
                if success:
                    address_data['zipcode'] = address_data['zip']
                    del address_data['zip']
                    data.update(address_data)
                else:
                    error['invalid_address'] = message
                    error_message.append("Could not verify your address. Please check it carefully.")
                    error_message += list(filter(bool, message.split('\n')))
            except Exception as e:
                logger.error("Error verifying main address on website (%s): %s", e, str(data))

        return error, error_message
