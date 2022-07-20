from odoo import models
from odoo.tools import ormcache
from collections import defaultdict
from math import ceil
from py3dbp import Packer, Bin, Item

MAX_WEIGHT = 999999999


def fits_in_box(items, length, width, height):
    """ No need to check weight since it was accounted for in the initial package database search """

    packer = Packer()
    packer.add_bin(Bin('bin', width, height, length, MAX_WEIGHT))
    packer.items = items
    packer.total_items = len(items)
    packer.pack()
    return not bool(packer.bins[0].unfitted_items)


def _find_height(items, items_volume, iterations, length, width, min_height, max_height):
    """ Recursive binary search for finding a minimum package height """

    iterations -= 1
    height = (min_height + max_height) / 2
    box_volume = length * width * height
    if box_volume > items_volume and fits_in_box(items, length, width, height):
        if iterations <= 0:
            return height
        return _find_height(items, items_volume, iterations, length, width, min_height, height)
    else:
        if iterations <= 0:
            return max_height
        return _find_height(items, items_volume, iterations, length, width, height, max_height)


def find_height(items, items_volume, length, width, min_height, max_height):
    # Try minimum height before running recursive testing
    if fits_in_box(items, length, width, min_height):
        return min_height
    else:
        iteration_count = max(3, min(6, round((max_height - min_height) * 10)))
        return _find_height(items, items_volume, iteration_count, length, width, min_height, max_height)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def update_prices(self):
        """ Updating the pricelist should not override delivery prices """

        delivery_product_ids = self.env['delivery.carrier'].search([
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)
        ]).product_id
        delivery_line_price_map = {
            line: line.price_unit
            for line in self.order_line.filtered(lambda x: x.is_delivery or x.product_id in delivery_product_ids)
        }
        result = super().update_prices()
        for line, price_unit in delivery_line_price_map.items():
            line.price_unit = price_unit
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @ormcache('cache_hash')
    def _estimate_package(self, cache_hash):
        """
        returns tuple: (package_id, length, width, height, weight)
        NOTE: returned dimensions may be smaller than package dimensions
        """

        if not self.product_id:
            return self.env['product.packaging'], 0, 0, 0, 0

        largest_product_dimension = max(self.product_id.mapped('product_dimension_max_u'))
        total_weight = sum(
            l.product_id.weight
            for l in self
            for x in range(ceil(l.product_qty))
        )
        total_volume = sum(
            l.product_id.volume
            for l in self
            for x in range(ceil(l.product_qty))
        )
        available_package_ids = self.env['product.packaging'].search([
            ('package_carrier_type', '=', 'ship_api'), '&', '&',
            '|', ('max_weight', '<=', 0), ('max_weight', '>=', total_weight),
            '|', ('dimension_max', '<=', 0), ('dimension_max', '>=', largest_product_dimension),
            ('volume', '>=', total_volume)
        ])

        # Construct list of products
        items = []
        for line in self:
            p = line.product_id
            for x in range(ceil(line.product_qty)):
                items.append(Item(p.id, p.product_width_u, p.product_height_u, p.product_length_u, p.weight))

        # Find all packages that items fit in, and store the smallest dimensions it will fit
        packages_dimensions = []
        for p_id in available_package_ids.sorted('volume'):
            if fits_in_box(items, p_id.packaging_length, p_id.width, p_id.height):
                if p_id.variable_dimensions:
                    height = find_height(items, total_volume, p_id.packaging_length, p_id.width, p_id.min_height, p_id.height)
                    packages_dimensions.append((p_id, p_id.packaging_length, p_id.width, height))
                else:
                    packages_dimensions.append((p_id, p_id.packaging_length, p_id.width, p_id.height))

        if not packages_dimensions:
            return self.env['product.packaging'], 0, 0, 0, 0

        # Find package with the smallest volume
        package = min(packages_dimensions, key=lambda x: x[1] * x[2] * x[3])

        return package[0].id, package[1], package[2], package[3], total_weight

    def estimate_package(self):
        line_ids = self.filtered(lambda x:
                                 x.product_id
                                 and x.product_qty > 0
                                 and x.product_id.type in ['product', 'consu']
                                 and any(
                                     (x.product_id.product_length_u,
                                      x.product_id.product_width_u,
                                      x.product_id.product_height_u,
                                      x.product_id.weight)
                                 ))
        product_ids = line_ids.product_id.sorted('id')

        product_counts = defaultdict(float)
        for line in line_ids:
            product_counts[line.product_id.id] += line.product_qty

        cache_hash = hash((
            tuple(sorted(product_counts.items(), key=lambda x: x[0])),
            tuple(product_ids.mapped('product_length_u')),
            tuple(product_ids.mapped('product_width_u')),
            tuple(product_ids.mapped('product_height_u')),
            tuple(product_ids.mapped('weight')),
        ))

        package_id, length, width, height, weight = line_ids._estimate_package(cache_hash)
        package_id = self.env['product.packaging'].browse(package_id)

        return package_id, length, width, height, weight
