from odoo import fields, models, _
from odoo.exceptions import UserError
import json, requests


class DeliveryCarrierApi(models.Model):
    _inherit = 'delivery.carrier.api'

    delivery_api = fields.Selection(selection_add=[('shipengine', 'Ship Engine')], ondelete={'shipengine': 'set null'})

    def _shipengine_call(self, use_prod_environment: bool, endpoint, request_type='GET', data=None):
        url = f"https://api.shipengine.com/{endpoint.lstrip('/')}"
        api_key = self.api_key_prod if use_prod_environment else self.api_key_test
        if not api_key:
            raise UserError(_("API key for %s has not been configured yet") % self.name)
        headers = {
            'Host': 'api.shipengine.com',
            'API-Key': api_key,
            'Content-Type': 'application/json'
        }
        return requests.request(request_type, url, headers=headers, data=json.dumps(data or {})).json()

    def shipengine_sync(self):
        data = self._shipengine_call(bool(self.api_key_prod), "/v1/carriers", 'GET')
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
        result = self._shipengine_call(self.global_prod_environment, '/v1/addresses/validate', 'POST', data=data)[0]

        status = result['status']
        message = result.get('messages') or []
        message = '\n'.join([msg['message'] for msg in message if msg['type'] != 'info'])
        result = result['matched_address']
        if result:
            address_indicator_map = {'yes': 'residential', 'no': 'commercial'}
            data = {
                'street': result['address_line1'],
                'street2': result['address_line2'],
                'city': result['city_locality'],
                'state': result['state_province'],
                'zip': result['postal_code'],
                'country': result['country_code'],
                'address_indicator': address_indicator_map.get(result['address_residential_indicator'], False)
            }
            if status == 'verified':
                return {'success': True, 'data': data, 'user_confirm': False, 'message': message}
            elif status == 'warning':
                return {'success': True, 'data': data, 'user_confirm': True, 'message': message}
        if status == 'verified':
            return {'success': True, 'user_confirm': False, 'message': message}
        else:
            return {'success': False, 'message': message}

    def _shipengine_rate_estimate(self, from_partner_id, to_partner_id, length, width, height, weight, attributes, active_service_ids):
        to_addr = to_partner_id.shipengine_get_address()
        from_addr = from_partner_id.shipengine_get_address()

        data = {
            "shipment": {
                "validate_address": "validate_only" if to_partner_id.ship_address_dirty else "no_validation",
                "ship_to": to_addr,
                "ship_from": from_addr,
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
                            "unit": "pound",
                            "value": weight
                        },
                        "dimensions": {
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
                'carrier_ids': active_service_ids.api_carrier_id.mapped('code'),
                "service_codes": active_service_ids.mapped('code'),
                "preferred_currency": self.currency_id.name.lower()
            }
        }
        response = self._shipengine_call(self.global_prod_environment, '/v1/rates', 'POST', data=data)
        rates = response.get('rate_response', {}).get('rates', [])
        code_service_map = {service_id.code: service_id.id for service_id in active_service_ids}
        return {
            code_service_map[rate['service_code']]: (
            rate['shipping_amount']['amount'], '; '.join(rate['warning_messages']), '; '.join(rate['error_messages']))
            for rate in rates
            if rate.get('service_code') in code_service_map
        }

    def shipengine_rate_estimate(self, from_partner_id, to_partner_id, length, width, height, weight, attributes, active_service_ids):
        if self.env['product.template']._get_length_uom_id_from_ir_config_parameter() == self.env.ref('uom.product_uom_foot'):
            length = round(max(length * 12, 1))
            width = round(max(width * 12, 1))
            height = round(max(height * 12, 1))
        else:
            length = round(max(length * 39.37, 1))
            width = round(max(width * 39.37, 1))
            height = round(max(height * 39.37, 1))

        origin_weight_uom = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        weight = round(max(origin_weight_uom._compute_quantity(weight, self.env.ref('uom.product_uom_lb')), 1))

        return self._shipengine_rate_estimate(from_partner_id, to_partner_id, length, width, height, weight, attributes, active_service_ids)
