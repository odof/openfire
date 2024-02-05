# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    of_analytic_section_id = fields.Many2one(comodel_name='of.account.analytic.section', string=u"Section analytique")
