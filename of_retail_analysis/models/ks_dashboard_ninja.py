# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class KsDashboardNinjaBoard(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    @api.model
    def ks_fetch_dashboard_data(self, ks_dashboard_id, ks_item_domain=[]):
        res = super(KsDashboardNinjaBoard, self).ks_fetch_dashboard_data(ks_dashboard_id, ks_item_domain)

        res['of_company_type_id'] = self._context.get('of_company_type_id', False)
        res['of_company_sector_id'] = self._context.get('of_company_sector_id', False)

        return res

    @api.model
    def ks_fetch_item_data(self, rec):
        if self._context.get('of_company_type_id'):
            rec = rec.with_context(of_company_type_id=self._context['of_company_type_id'])
        if self._context.get('of_company_sector_id'):
            rec = rec.with_context(of_company_sector_id=self._context['of_company_sector_id'])

        return super(KsDashboardNinjaBoard, self).ks_fetch_item_data(rec)
