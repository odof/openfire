# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFDatastoreBrand(models.Model):
    _inherit = 'of.datastore.brand'

    @api.model
    def display_of_datastore_brand(self):
        action = self.env.ref('of_datastore_product.of_datastore_brand_action').read()[0]
        return action

    @api.multi
    def action_open_centralized_products(self):
        self.ensure_one()
        return {
            'name': 'Catalogue',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'kanban,tree,form',
            'res_model': 'product.template',
            'target': 'current',
            'context': {'search_default_brand_id': self.brand_id.id, 'search_default_of_datastore_search':True}
        }
