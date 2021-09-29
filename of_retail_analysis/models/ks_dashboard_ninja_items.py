# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class KsDashboardNinjaItems(models.Model):
    _inherit = 'ks_dashboard_ninja.item'

    # This function working has to be changed domain with widget
    def ks_convert_into_proper_domain(self, ks_domain, rec):
        res = super(KsDashboardNinjaItems, self).ks_convert_into_proper_domain(ks_domain, rec)
        # Pour type comme pour secteur, c'est bien sur la société qu'on fait une restriction
        # et pas sur les modèles type et secteur eux mêmes
        if rec.ks_model_id.model and rec._context.get('of_company_type_id') and \
                'company_id' in self.env[rec.ks_model_id.model]._fields:
            company_ids = self.env['res.company'].search(
                [('of_company_type_id', 'in', [rec._context.get('of_company_type_id')])])
            res.append(('company_id', '=', company_ids.ids))

        if rec.ks_model_id.model and rec._context.get('of_company_sector_id') and \
                'company_id' in self.env[rec.ks_model_id.model]._fields:
            company_ids = self.env['res.company'].search(
                [('of_company_sector_id', 'in', [rec._context.get('of_company_sector_id')])])
            res.append(('company_id', '=', company_ids.ids))

        return res

    def ks_convert_into_proper_domain_2(self, ks_domain_2, rec):
        res = super(KsDashboardNinjaItems, self).ks_convert_into_proper_domain_2(ks_domain_2, rec)
        # Pour type comme pour secteur, c'est bien sur la société qu'on fait une restriction
        # et pas sur les modèles type et secteur eux mêmes
        if rec.ks_model_id.model and rec._context.get('of_company_type_id') and \
                'company_id' in self.env[rec.ks_model_id_2.model]._fields:
            company_ids = self.env['res.company'].search(
                [('of_company_type_id', 'in', [rec._context.get('of_company_type_id')])])
            res.append(('company_id', '=', company_ids.ids))

        if rec.ks_model_id.model and rec._context.get('of_company_sector_id') and \
                'company_id' in self.env[rec.ks_model_id_2.model]._fields:
            company_ids = self.env['res.company'].search(
                [('of_company_sector_id', 'in', [rec._context.get('of_company_sector_id')])])
            res.append(('company_id', '=', company_ids.ids))

        return res
