# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class OFDatastoreSaleHook(models.AbstractModel):
    _name = 'of.datastore.sale.hook'

    def _init_transfer_partner_id_to_partner_ids(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_datastore_sale'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version < '10.0.2.0.0'
        if actions_todo:
            connectors = self.env['of.datastore.sale'].search([])
            for connector in connectors:
                connector.partner_ids = [(4, connector.partner_id.id)]
