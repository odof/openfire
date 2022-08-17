# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_storage = fields.Boolean(string=u"Stockage et retrait à la demande")

    def get_saleorder_kit_data(self):
        res = super(ProductTemplate, self).get_saleorder_kit_data()
        if self.of_storage:
            for kit_line in res.get('kit_line_ids'):
                if len(kit_line) >= 3 and kit_line[2] and kit_line[2]['product_id']:
                    product_id = self.env['product.product'].browse(kit_line[2]['product_id'])
                    kit_line[2]['of_storage'] = product_id.of_storage
        else:
            for kit_line in res.get('kit_line_ids'):
                if len(kit_line) >= 3 and kit_line[2] and kit_line[2]['product_id']:
                    kit_line[2]['of_storage_readonly'] = True
        return res
