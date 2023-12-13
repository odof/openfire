# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    group_of_advanced_sale_layout_category = fields.Boolean(
        string="(OF) Advanced Sections",
        implied_group='of_sale_quote_template.group_of_advanced_sale_layout_category',
        group='base.group_user')
    module_of_sale_budget = fields.Boolean(
        string=u"(OF) Budget management", help="Installs the Sales / Budget module")
    of_quote_template = fields.Selection(
        [('add', u'Ajoute les lignes de commande du modèle au devis'),
         ('replace', u'Remplace les lignes de commande du devis par celles du modèle')],
        string=u"(OF) Modèle de devis", required=True, default='replace',
        help=u"Ceci ne modifie que le fonctionnement des lignes de commandes du modèle."
             u"Les autres informations (ex: position fiscale) ne sont pas impactées par ce paramètre et seront "
             u"toujours remplacées par celles du dernier modèle choisi")
    of_companies_ok = fields.Boolean(
        string=u"(OF) Modèle de devis / Société(s) autorisée(s)", default=False,
        help=u"Définir les sociétés autorisées dans les modèles de devis")

    @api.multi
    def set_of_quote_template_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_quote_template', self.of_quote_template)

    @api.multi
    def set_of_companies_ok(self):
        view = self.env.ref('of_sale_quote_template.view_sale_quote_template_form2', raise_if_not_found=False)
        rule = self.env.ref('of_sale_quote_template.of_restrict_access_of_sale_quote_template_rule', raise_if_not_found=False)
        if not self.of_companies_ok:
            templates = self.env['sale.quote.template'].search([])
            templates.write({'of_company_ids': [(5, 0)]})
        if view:
            view.write({'active': self.of_companies_ok})
        if rule:
            rule.write({'active': self.of_companies_ok})

    @api.model
    def get_default_of_companies_ok(self, fields):
        view = self.env.ref('of_sale_quote_template.view_sale_quote_template_form2', raise_if_not_found=False)
        return {
            'of_companies_ok': view and view.active or False,
        }

    @api.multi
    def execute(self):
        """ On désactive le menu des sections standards quand on active les sections avancées"""
        res = super(OFSaleConfiguration, self).execute()
        menu_id = self.env.ref('sale.Report_configuration')
        menu_id.active = not self.group_of_advanced_sale_layout_category
        return res
