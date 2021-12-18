# Odoo Shipping API
This module is intended to be a development platform for connecting multiple shipping API's.

Requires the 'product_dimension' module from [OCA/product-attribute](https://github.com/OCA/product-attribute)

<h2>Supported API's</h2>

Currently only [Ship Engine](www.shipengine.com) is supported, but adding your own shipping api should be trivial.
- [Ship Engine](www.shipengine.com)
  - Address Validation
  - LTL (Less then TruckLoad) shipments

It is recommended to verify your warehouse addresses to ensure accuracy

<h2>Required Methods</h2>

All required methods are abstracted out into the database model 'delivery.carrier.api'.

```python
from odoo import api, fields, models

class DeliveryCarrierApi(models.Model):
    _inherit = 'delivery.carrier.api'

    """ Replace SHIPPINGAPINAME with the name of your shipping integration"""
    
    def SHIPPINGAPINAME_sync(self):
        """ Grab carriers and their related services from the api
        
        Carriers and their services are automatically created, updated, or deleted as necessary from the provided information
        A warning will be shown to the user if any carriers or services are deleted
        
        returns list of dicts containing carrier information:
        [
            {
                'code': str; carrier identifier for this api
                'name': str; friendly carrier name
                'services': list of dicts containing service information [
                    {
                        'code': str; service identifier for this api
                        'name': str; friendly service name
                    }
                ]
            }
        ]
        """
        return
    
    def SHIPPINGAPINAME_supports(self):
        """ Define supported features for the implementation """
        self.supports_test_environment = True
        self.supports_address_validation = True
        self.supports_tracking = True
        self.supports_insurance = True
        self.supports_returns = True
        self.supports_ltl = True
    
    def SHIPPINGAPINAME_verify_address(self, name, company_name, phone, street, street2, city, state_code, zip, country_code):
        """ Verify an address with the shipping api
        Required if supports_address_validation == True
        
        If the shipping api does not suggest whether the address should be double-checked,
            you can call self.compare_address_diff() before deciding to return a 'res.partner.verify' record
        
        returns dict {
            'success': bool; is this a valid address
            'data': dict (optional); corrected address values; if omitted, the original values are used
            'user_confirm: bool (optional); request user to verify changes; if omitted, built-in diff detection is used
            'message': str (required if success==False) any warning or error messages
        }
        """
        return

    def SHIPPINGAPINAME_rate_estimate(self, from_partner_id, to_partner_id, length, width, height, weight, active_service_ids):
        """ Get rates for all active services
        This method is automatically cached to eliminate repeated calls
        
        returns:
        - dict where key=int(service_id) and value=tuple(price, warning_message, error_message)
            {
                1: (5.76, "", ""),
                2: (10.29, "Surcharge may apply to recipient", ""),
                3: (0, "", "Package size too large"),
            }
        """
        return
```

TODO:
- Proper multi-currency support
- Website user should be able to confirm major address changes
