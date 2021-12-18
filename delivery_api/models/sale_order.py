from odoo import models
from odoo.tools import ormcache
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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @ormcache('cache_hash')
    def _estimate_package(self, cache_hash):
        """
        returns tuple: (package_id, length, width, height, weight)
        NOTE: returned dimensions may be smaller than package dimensions
        """

        largest_product_dimension = self.env.ref('uom.product_uom_meter')._compute_quantity(
            max(self.product_id.mapped('product_dimension_max_m')),
            self.env['product.template']._get_length_uom_id_from_ir_config_parameter()
        )
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
                items.append(Item(p.id, p.product_width_m, p.product_height_m, p.product_length_m, p.weight))

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
        lines = self.filtered(lambda x: x.product_qty > 0 and x.product_id.type in ['product', 'consu'])
        cache_hash = hash((
            tuple(lines.ids),
            tuple(lines.product_id.ids),
            tuple(lines.product_id.mapped('product_length_m')),
            tuple(lines.product_id.mapped('product_width_m')),
            tuple(lines.product_id.mapped('product_height_m')),
            tuple(lines.product_id.mapped('weight')),
            tuple(lines.mapped('product_qty')),
        ))

        package_id, length, width, height, weight = lines._estimate_package(cache_hash)
        package_id = self.env['product.packaging'].browse(package_id)

        return package_id, length, width, height, weight
