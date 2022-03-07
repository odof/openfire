# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_of_advanced_sale_layout_category = fields.Boolean(
        string=u"(OF) Activer les sections avancées sur les devis",
        implied_group='of_sale_quote_template.group_of_advanced_sale_layout_category',
        group='base.group_user')
    module_of_sale_budget = fields.Boolean(
        string=u"(OF) Gestion du budget", help="Installe le module Ventes / Budget")

    @api.multi
    def execute(self):
        """ On désactive le menu des sections standards quand on active les sections avancées"""
        res = super(OFSaleConfiguration, self).execute()
        menu_id = self.env.ref('sale.Report_configuration')
        if self.group_of_advanced_sale_layout_category:
            menu_id.active = False
        else:
            menu_id.active = True
        return res
