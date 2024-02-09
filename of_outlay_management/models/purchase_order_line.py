# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")
    of_outlay_analysis_selected = fields.Boolean(
        string=u"Sélectionné", help=u"Sélectionné pour l'analyse des débours", default=True
    )
