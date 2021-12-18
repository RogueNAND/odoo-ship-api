from odoo import fields, models, _
from odoo.exceptions import UserError
import json, requests


class DeliveryCarrierApi(models.Model):
    _inherit = 'delivery.carrier.api'

    delivery_api = fields.Selection(selection_add=[('shipengine', 'Ship Engine')], ondelete={'shipengine': 'set null'})

    def _shipengine_call(self, prod_environment, endpoint, request_type='GET', data=None):
        url = f"https://api.shipengine.com/v1/{endpoint.lstrip('/')}"
        api_key = self.api_key_prod if prod_environment else self.api_key_test
        if not api_key:
            raise UserError(_("API key for %s has not been configured yet") % self.name)
        headers = {
            'Host': 'api.shipengine.com',
            'API-Key': api_key,
            'Content-Type': 'application/json'
        }
        return requests.request(request_type, url, headers=headers, data=json.dumps(data or {})).json()

    def shipengine_sync(self):
        data = self._shipengine_call(bool(self.api_key_prod), "/carriers", 'GET')
        return [
            {
                'code': carrier['carrier_id'],
                'name': carrier['friendly_name'],
                'services': [{
                    'code': service['service_code'],
                    'name': service['name']
                } for service in carrier['services']]
            }
            for carrier in data['carriers']
        ]

    def shipengine_supports(self):
        self.supports_test_environment = True
        self.supports_address_validation = True
        self.supports_tracking = False
        self.supports_insurance = False
        self.supports_returns = False
        self.supports_ltl = True

    def shipengine_verify_address(self, name, company_name, phone, street, street2, city, state_code, zip, country_code):
        data = [{
            "name": name,
            "phone": phone,
            "company_name": company_name,
            "address_line1": street,
            "address_line2": street2,
            "city_locality": city,
            "state_province": state_code,
            "postal_code": zip,
            "country_code": country_code,
        }]
        result = self._shipengine_call(self.global_prod_environment, '/addresses/validate', request_type='POST', data=data)[0]

        status = result['status']
        message = result.get('messages') or []
        message = '\n'.join([msg['message'] for msg in message if msg['type'] != 'info'])
        result = result['matched_address']
        if result:
            data = {
                'street': result['address_line1'],
                'street2': result['address_line2'],
                'city': result['city_locality'],
                'state': result['state_province'],
                'zip': result['postal_code'],
                'country': result['country_code'],
                'address_residential': result['address_residential_indicator'] == 'yes'
            }
            if status == 'verified':
                return {'success': True, 'data': data, 'user_confirm': False, 'message': message}
            elif status == 'warning':
                return {'success': True, 'data': data, 'user_confirm': True, 'message': message}
        if status == 'verified':
            return {'success': True, 'user_confirm': False, 'message': message}
        else:
            return {'success': False, 'message': message}

    def shipengine_rate_estimate(self, from_partner_id, to_partner_id, length, width, height, weight, active_service_ids):
        code_service_map = {service_id.code: service_id.id for service_id in active_service_ids}
        data = {
            "shipment": {
                "validate_address": "validate_only" if to_partner_id.ship_address_dirty else "no_validation",
                "ship_to": {
                    "name": to_partner_id.display_name or "",
                    "phone": to_partner_id.phone or to_partner_id.mobile or to_partner_id.parent_id.phone or to_partner_id.parent_id.mobile or "",
                    "company_name": to_partner_id.parent_id.name or "",
                    "address_line1": to_partner_id.street or "",
                    "address_line2": to_partner_id.street2 or "",
                    "address_line3": "",
                    "city_locality": to_partner_id.city or "",
                    "state_province": to_partner_id.state_id.code or "",
                    "postal_code": to_partner_id.zip or "",
                    "country_code": to_partner_id.country_id.code or "",
                    "address_residential_indicator": "unknown" if to_partner_id.ship_address_dirty else "yes" if to_partner_id.address_residential else "no"
                },
                "ship_from": {
                    "name": from_partner_id.display_name or "",
                    "phone": from_partner_id.phone or from_partner_id.mobile or from_partner_id.parent_id.phone or from_partner_id.parent_id.mobile or "",
                    "company_name": from_partner_id.parent_id.name or from_partner_id.name or "",
                    "address_line1": from_partner_id.street or "",
                    "address_line2": from_partner_id.street2 or "",
                    "address_line3": "",
                    "city_locality": from_partner_id.city or "",
                    "state_province": from_partner_id.state_id.code or "",
                    "postal_code": from_partner_id.zip or "",
                    "country_code": from_partner_id.country_id.code or "",
                    "address_residential_indicator": "unknown" if from_partner_id.ship_address_dirty else "yes" if from_partner_id.address_residential else "no"
                },
                # "confirmation": "none",
                # "customs": {
                #     "contents": "merchandise",
                #     "non_delivery": "return_to_sender",
                #     "customs_items": []
                # },
                # "advanced_options": {},
                "insurance_provider": "none",
                "packages": [
                    {
                        "weight": {
                            "value": weight,
                            # "unit": self.env['product.template']._get_weight_uom_id_from_ir_config_parameter().name
                            "unit": "ounce"
                        },
                        "dimensions": {
                            # "unit": self.env['product.template']._get_length_uom_id_from_ir_config_parameter().name,
                            "unit": "inch",
                            "length": length,
                            "width": width,
                            "height": height
                        },
                        # "insured_value": {
                        #     "currency": self.env.user.currency_id.name.lower(),
                        #     "amount": 0
                        # },
                        # "label_messages": {
                        #     "reference1": null,
                        #     "reference2": null,
                        #     "reference3": null
                        # },
                    }
                ]
            },
            "rate_options": {
                'carrier_ids': self.api_carrier_ids.mapped('code'),
                "service_codes": active_service_ids.mapped('code'),
                "preferred_currency": self.currency_id.name.lower()
            }
        }
        response = self._shipengine_call(self.global_prod_environment, '/rates', request_type='POST', data=data)
        rates = response.get('rate_response', {}).get('rates', [])
        return {
            code_service_map[rate['service_code']]: (rate['shipping_amount']['amount'], '; '.join(rate['warning_messages']), '; '.join(rate['error_messages']))
            for rate in rates
            if rate.get('service_code') in code_service_map
        }
