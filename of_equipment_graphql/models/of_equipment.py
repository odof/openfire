# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many

logger = logging.getLogger(__name__)


class OFEquipment(models.Model):
    _inherit = 'of.equipment'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if warranty_type := args.get('warranty_type'):
            mutation['warranty_type'] = warranty_type

        if state := args.get('state'):
            mutation['state'] = state

        if model_name := args.get('model_name'):
            mutation['model_name'] = model_name

        if installation_type := args.get('installation_type'):
            mutation['installation_type'] = installation_type

        if 'is_compliant' in args.keys():
            mutation['is_compliant'] = args['is_compliant']

        if piece_number := args.get('piece_number'):
            mutation['piece_number'] = piece_number

        if note := args.get('note'):
            mutation['note'] = note

        if service_date := args.get('service_date'):
            mutation['service_date'] = service_date

        if installation_date := args.get('installation_date'):
            mutation['installation_date'] = installation_date

        if end_warranty_date := args.get('end_warranty_date'):
            mutation['end_warranty_date'] = end_warranty_date

        if product := args.get('product'):
            mutation['product_id'] = many2one(self=self, model='product.product', input=product)

        if customer := args.get('customer'):
            mutation['customer_id'] = many2one(self=self, model='res.partner', input=customer)

        if product_category := args.get('product_category'):
            mutation['product_category_id'] = many2one(self=self, model='product.category', input=product_category)

        if brand := args.get('brand'):
            mutation['brand_id'] = many2one(self=self, model='of.product.brand', input=brand)

        if lot := args.get('lot'):
            mutation['lot_id'] = many2one(self=self, model='stock.lot', input=lot)

        if reseller := args.get('reseller'):
            mutation['reseller_id'] = many2one(self=self, model='res.partner', input=reseller)

        if installer := args.get('installer'):
            mutation['installer_id'] = many2one(self=self, model='res.partner', input=installer)

        if intervention := args.get('intervention'):
            mutation['intervention_ids'] = x2many(
                self=self, model='calendar.event', input=intervention, default={'of_use_equipment': True}, keep=True
            )

        if site_address := args.get('site_address'):
            mutation['site_address_id'] = many2one(self=self, mode='res.partner', input=site_address)

        return mutation
