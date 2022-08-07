from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging

logger = logging.getLogger(__name__)


class PortalSaleShippingApi(CustomerPortal):

    OPTIONAL_BILLING_FIELDS = CustomerPortal.OPTIONAL_BILLING_FIELDS + ['ship_stored_hash']

    def details_form_validate(self, data):
        error, error_message = super().details_form_validate(data)

        country = data.get('country_id')
        state = data.get('state_id')

        if country and state and not error:
            country_id = request.env['res.country'].browse(int(country))
            state_id = request.env['res.country'].browse(int(state))
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
                    address_data['ship_stored_hash'] = request.env['res.partner'].sudo().get_address_hash(
                        address_data.get('street'),
                        address_data.get('street2'),
                        address_data.get('city'),
                        address_data.get('state_id'),
                        address_data.get('zipcode'),
                        address_data.get('country_id'),
                        address_data.get('address_indicator'),
                    )
                    data.update(address_data)
                else:
                    error['invalid_address'] = message
                    error_message.append("Could not verify your address. Please check it carefully.")
                    error_message += list(filter(bool, message.split('\n')))
            except Exception as e:
                logger.error("Error verifying main address on website (%s): %s", e, str(data))

        return error, error_message
