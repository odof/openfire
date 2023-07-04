# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    of_eco_organism_id = fields.Many2one(
        comodel_name='of.eco.organism', string=u"Éco-organisme", readonly=True)
    of_eco_contribution_id = fields.Many2one(
        comodel_name='of.eco.contribution', string=u"Éco-contribution", readonly=True)
    of_total_eco_contribution = fields.Float(
        string=u"Montant éco-contribution", readonly=True)

    def _select(self):
        res = super(AccountInvoiceReport, self)._select()
        res += ", sub.of_eco_contribution_id as of_eco_contribution_id, sub.of_eco_organism_id as of_eco_organism_id" \
               ", sub.of_total_eco_contribution as of_total_eco_contribution"
        return res

    def _sub_select(self):
        res = super(AccountInvoiceReport, self)._sub_select()
        res += ", ail.of_eco_contribution_id as of_eco_contribution_id, oec.organism_id as of_eco_organism_id" \
               ", ail.of_total_eco_contribution as of_total_eco_contribution"
        return res

    def _from(self):
        res = super(AccountInvoiceReport, self)._from()
        res += "LEFT JOIN of_eco_contribution oec on ail.of_eco_contribution_id = oec.id\n" \
               "LEFT JOIN of_eco_organism oeo on oec.organism_id = oeo.id\n"
        return res

    def _group_by(self):
        res = super(AccountInvoiceReport, self)._group_by()
        res += ", ail.of_eco_contribution_id, oec.organism_id"
        return res
