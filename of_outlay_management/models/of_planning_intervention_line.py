# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfPlanningInterventionLine(models.Model):
    _inherit = "of.planning.intervention.line"

    analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")

    @api.multi
    def _prepare_invoice_line(self):
        res = super(OfPlanningInterventionLine, self)._prepare_invoice_line()
        res['of_analytic_section_id'] = self.analytic_section_id
        return res
