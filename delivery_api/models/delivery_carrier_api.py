from odoo import api, fields, models, _
from odoo.tools import groupby, ormcache
from odoo.exceptions import UserError
from datetime import timedelta
import logging, math

logger = logging.getLogger(__name__)


class DeliveryCarrierApi(models.Model):
    _name = 'delivery.carrier.api'
    _description = 'Delivery Carrier API'

    name = fields.Char(required=True)
    delivery_api = fields.Selection([])
    carrier_ids = fields.One2many('delivery.carrier', 'delivery_api_id', readonly=True)
    api_carrier_ids = fields.One2many('delivery.carrier.api.carrier', 'delivery_api_id', string="Supported Carriers")
    global_prod_environment = fields.Boolean(compute='_compute_global_prod_environment', store=True)
    api_key_prod = fields.Char()
    api_key_test = fields.Char()
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id.id)

    supports_test_environment = fields.Boolean(string="Sandbox Environment", compute='_compute_api_features', help="Test your shipping integration before using it in production")
    supports_address_validation = fields.Boolean(string="Address Validation", compute='_compute_api_features', help="Validate partner addresses before shipment")
    supports_tracking = fields.Boolean(string="Realtime Tracking", compute='_compute_api_features', help="Get realtime tracking updates for shipments")
    supports_insurance = fields.Boolean(string="Insurance", compute='_compute_api_features', help="Insure your shipments")
    supports_returns = fields.Boolean(string="Returns", compute='_compute_api_features', help="Generate return labels automatically")

    possible_outage_detected = fields.Boolean()
    last_cache_clear_time = fields.Datetime(default=lambda x: fields.Datetime.now())

    @api.depends('carrier_ids.prod_environment')
    def _compute_global_prod_environment(self):
        for api in self:
            # Only disable global_prod_environment if ALL linked carrier_ids are test environments
            api.global_prod_environment = bool(api.carrier_ids.filtered('prod_environment'))

    def _compute_api_features(self):
        self.supports_test_environment = False
        self.supports_address_validation = False
        self.supports_tracking = False
        self.supports_insurance = False
        self.supports_returns = False
        for record in self.filtered('delivery_api'):
            getattr(record, '%s_supports' % record.delivery_api)()

    @api.model
    def _manage_cache(self):
        """ Ensure rate estimate caches are cleared periodically.
        Clear caches sooner if a possible carrier outage was detected
        """

        now = fields.Datetime.now()
        if self.search(['|', ('possible_outage_detected', '=', True), ('last_cache_clear_time', '<', now - timedelta(hours=1))]):
            logger.info("Clearing Delivery API Caches")
            self.clear_caches()

            api_ids = self.search([])
            api_ids.possible_outage_detected = False
            api_ids.last_cache_clear_time = now

    @api.model
    def compare_address_diff(self, old_street: str, old_street2: str, old_city: str, old_state: str, old_zip: str, old_country: str,
                             new_street: str, new_street2: str, new_city: str, new_state: str, new_zip: str, new_country: str):
        """
        returns fields that are significantly different between the partner address and the given address
        """

        old_street = (old_street or "").strip().lower()
        old_street2 = (old_street2 or "").strip().lower()
        old_city = (old_city or "").strip().lower()
        old_state = (old_state or "").strip().lower()
        old_zip = (old_zip or "").strip().lower()
        old_country = (old_country or "").strip().lower()

        new_street = (new_street or "").strip().lower()
        new_street2 = (new_street2 or "").strip().lower()
        new_city = (new_city or "").strip().lower()
        new_state = (new_state or "").strip().lower()
        new_zip = (new_zip or "").strip().lower()
        new_country = (new_country or "").strip().lower()

        diff_street = new_street != old_street
        diff_street2 = new_street2 != (old_street2 or '')
        diff_city = old_city != new_city
        diff_state = old_state != new_state
        diff_zip = old_zip != new_zip and not (new_country == 'US' and new_zip.startswith(old_zip.split('-')[0]))
        diff_country = old_country != new_country

        diffs = {
            'street': diff_street,
            'street2': diff_street2,
            'city': diff_city,
            'state': diff_state,
            'zip': diff_zip,
            'country': diff_country,
        }

        return {diff_key: diff_val for diff_key, diff_val in diffs.items() if diff_val} or False

    def detect_outage(self, active_service_ids, good_service_ids):
        """ Bad data shouldn't be cached for too long.
        If any carrier is 100% unsuccessful, mark a possible outage so the cache can be cleared sooner.
        """

        self.ensure_one()
        self = self.sudo()
        if good_service_ids:
            good_service_ids = self.env['delivery.carrier.api.carrier.service'].browse(good_service_ids)
            bad_carrier_ids = active_service_ids.api_carrier_id - good_service_ids.api_carrier_id
            if bad_carrier_ids:
                logger.warning("Detected possible outage for carriers. Signaling for cache reset: %s", ', '.join(bad_carrier_ids.mapped('name')))
                self.possible_outage_detected = True

    def action_sync(self):
        for record in self:
            result = getattr(record, '%s_sync' % record.delivery_api)()
            self.sudo().sync_carriers(result)

            warn_carrier_ids = self.carrier_ids.filtered(lambda x: not x.api_carrier_id or not x.service_id)
            if warn_carrier_ids:
                warn_carrier_names = warn_carrier_ids.mapped('name')
                return {'warning': {
                    'title': 'Fix Shipping Methods',
                    'message': f"The following shipping methods are invalid and need to be reconfigured:\n\n{warn_carrier_names}"}
                }

    def sync_carriers(self, carriers):
        self.ensure_one()

        api_carrier_ids = self.env['delivery.carrier.api.carrier']
        for carrier in carriers:
            services = carrier.pop('services')
            api_carrier_id = self.env['delivery.carrier.api.carrier'].search([
                ('delivery_api_id', '=', self.id),
                ('code', '=', carrier['code'])
            ]) or self.env['delivery.carrier.api.carrier'].create({'delivery_api_id': self.id, **carrier})
            api_carrier_id.write(carrier)
            api_carrier_id.sync_services(services)
            api_carrier_ids |= api_carrier_id

        carriers_to_delete = self.env['delivery.carrier.api.carrier'].search([('delivery_api_id', '=', self.id)]) - api_carrier_ids
        carriers_to_delete.unlink()

    def _verify_address(self, name, company_name, phone, street, street2, city, state_code, zip, country_code):
        """ This could possibly be cleaned up, but it needs to stay flexible enough for website address verification """

        self.ensure_one()

        name = name or ""
        company_name = company_name or ""
        phone = phone or ""
        street = street or ""
        street2 = street2 or ""
        city = city or ""
        state_code = state_code or ""
        zip = zip or ""
        country_code = country_code or ""

        logger.info(f"Verifying shipping address via %s: '%s' '%s' street='%s' street2='%s' city='%s' state='%s' zip='%s' country='%s'",
                    self.delivery_api, name, company_name, street, street2, city, state_code, zip, country_code)
        attr_name = f"{self.delivery_api}_verify_address"
        if not hasattr(self, attr_name):
            raise UserError(_("%s does not have the ability to verify addresses") % self.delivery_api)

        result = getattr(self, attr_name)(name, company_name, phone, street, street2, city, state_code, zip, country_code)
        success = result['success']

        if success:
            data = result['data']

            # Ensure all required return fields are set
            required_values = {'street', 'street2', 'city', 'state', 'zip', 'country', 'address_indicator'}
            returned_values = set(data.keys())
            if required_values != returned_values:
                raise UserError(_("Address verification did not return correct values:\n\nRequired:\n[%s]\n\nReturned:\n[%s]")
                                % (', '.join(required_values), ', '.join(returned_values)))

            # Some API's will specify if a user confirmation is recommended, otherwise we can check ourselves
            user_confirm = result['success'] and result.get('user_confirm', self.compare_address_diff(
                street, street2, city, state_code, zip, country_code,
                data['street'], data['street2'], data['city'], data['state'], data['zip'], data['country']
            ))

            # Convert state and country codes into internal records
            state_code = data['state'].upper()
            country_code = data['country'].upper()
            state_id = self.env['res.country.state'].search([('code', '=', state_code), ('country_id.code', '=', country_code)])
            if len(state_id) != 1:
                raise UserError(_("Cannot verify state '%s' and country '%s'") % (state_code, country_code))
            del data['state']
            del data['country']
            data.update({'state_id': state_id.id, 'country_id': state_id.country_id.id})

            return True, result.get('message', ""), user_confirm, data
        else:
            return False, result.get('message', False), False, {}

    @ormcache('self.carrier_ids.service_id', 'self.carrier_ids.service_id', 'cache_hash')
    def _rate_estimate(self, cache_hash, from_partner_id, to_partner_id, length, width, height, weight, attributes, log_msg):
        """ Log message, call api, check for outage, and cache result """

        self.ensure_one()
        attr_name = f"{self.delivery_api}_rate_estimate"
        logger.info(*log_msg)

        force_freight = bool(attributes['freight_package'])
        active_service_ids = self.carrier_ids.service_id.filtered(lambda x: bool(x.api_carrier_id.freight_type) == force_freight)
        service_rate_map = getattr(self, attr_name)(from_partner_id, to_partner_id, length, width, height, weight, attributes, active_service_ids) or {}
        self.detect_outage(active_service_ids, [service for service, rate in service_rate_map.items() if rate[0] and not rate[2]])
        return service_rate_map

    def rate_estimate(self, from_partner_id, to_partner_id, order_line_ids):
        self.ensure_one()

        order_line_ids = order_line_ids.filtered(lambda x: x.product_qty > 0 and x.product_id.type in ['product', 'consu'])
        package_id, length, width, height, weight = order_line_ids.estimate_package()
        if not package_id:
            return {
                service_id.id: (0, False, _("Oversized package. Call for quote."))
                for service_id in self.api_carrier_ids.service_ids
            }

        log_msg = ("%s: Getting rate estimate from partner_id [%s] to [%s] for products %s in order %s. Chosen package: '%s' (%fx%fx%f%s, max %f%s; Freight=%s)",
                   self.name, from_partner_id.id, to_partner_id.id, order_line_ids.product_id.ids, order_line_ids.order_id.ids,
                   package_id.name, length, width, height, package_id.length_uom_name, weight, package_id.weight_uom_name, package_id.freight_package_type)

        attributes = {
            'freight_package': package_id.freight_package_type,
            'perishable': any(order_line_ids.product_id.mapped('shipping_perishable')),
            'hazardous': any(order_line_ids.product_id.mapped('shipping_hazardous')),
            'freight_class': order_line_ids.product_id.freight_code.get_code_for_shipping(),
        }
        cache_hash = hash((
            from_partner_id.id,
            (from_partner_id.street or "").strip().upper(),
            (from_partner_id.street2 or "").strip().upper(),
            (from_partner_id.city or "").strip().upper(),
            from_partner_id.state_id.id,
            (from_partner_id.zip or "").strip().upper(),
            from_partner_id.country_id.id,
            to_partner_id.id,
            (to_partner_id.street or "").strip().upper(),
            (to_partner_id.street2 or "").strip().upper(),
            (to_partner_id.city or "").strip().upper(),
            to_partner_id.state_id.id,
            (to_partner_id.zip or "").strip().upper(),
            to_partner_id.country_id.id,
            length, width, height, weight,
            *attributes.values(),
        ))
        return self.sudo()._rate_estimate(cache_hash, from_partner_id, to_partner_id, length, width, height, weight, attributes, log_msg)
