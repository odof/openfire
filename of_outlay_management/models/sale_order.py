# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_data_from_template(self, line, price, discount):
        data = super(SaleOrder, self)._get_data_from_template(line, price, discount)
        data['of_analytic_section_id'] = line.of_analytic_section_id
        return data
