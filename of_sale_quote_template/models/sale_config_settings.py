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
    of_quote_template = fields.Selection(
        [('add', u'Ajoute les lignes de commande du modèle au devis'),
         ('replace', u'Remplace les lignes de commande du devis par celles du modèle')],
        string=u"(OF) Modèle de devis", required=True, default='replace',
        help=u"Ceci ne modifie que le fonctionnement des lignes de commandes du modèle."
             u"Les autres informations (ex: position fiscale) ne sont pas impactées par ce paramètre et seront "
             u"toujours remplacées par celles du dernier modèle choisi")

    @api.multi
    def set_of_quote_template_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_quote_template', self.of_quote_template)

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
