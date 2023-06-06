# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class OpportunityReport(models.Model):
    _inherit = "crm.opportunity.report"

    of_my_company = fields.Boolean(
        string=u"Est mon magasin ?", compute='_get_is_my_company', search='_search_is_my_company')

    @api.model
    def _search_is_my_company(self, operator, value):
        if operator != '=' or not value:
            raise ValueError(_("Unsupported search operator"))
        return [('company_id', '=', self.env.user.company_id.id)]

    def _get_is_my_company(self):
        for rec in self:
            rec.of_my_company = self.env.user.company_id == rec.company_id
