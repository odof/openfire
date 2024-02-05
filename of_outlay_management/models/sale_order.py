# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_outlay_analysis_type = fields.Selection(
        selection=[('init', u"Initial"), ('compl', u"Complémentaire")], string=u"Type de budget",
        help=u"Type de budget pour affichage dans les débours"
    )

    def _get_data_from_template(self, line, price, discount):
        data = super(SaleOrder, self)._get_data_from_template(line, price, discount)
        data['of_analytic_section_id'] = line.of_analytic_section_id
        return data
