# -*- coding: utf-8 -*-
from odoo import models, fields, api


# Ajouter la configuration "Description articles"
class OFPurchaseConfiguration(models.TransientModel):
    _inherit = 'purchase.config.settings'

    of_description_as_order_setting = fields.Selection(
        [(0, "Description article telle que saisie dans le catalogue"),
         (1, "Description article telle que saisie dans le devis")],
        string="(OF) Description articles",
        help=u"Choisissez le type de description affiché dans la commande fournisseur.\n"
             u"Cela affecte également les documents imprimables.")

    group_purchase_order_line_display_stock_info = fields.Boolean(
        string=u"(OF) Informations de stock",
        implied_group='of_purchase.group_purchase_order_line_display_stock_info',
        group='base.group_portal,base.group_user,base.group_public',
        help=u"Affiche les informations de stock au niveau des lignes de commande")

    of_date_purchase_order = fields.Selection([
        (0, 'Standard'),
        (1, 'Date du jour')], string="(OF) Date des commandes fournisseur")

    of_tax_mandatory = fields.Boolean(string="(OF) Taxes")

    @api.multi
    def set_description_as_order_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'purchase.config.settings', 'of_description_as_order_setting', self.of_description_as_order_setting)

    @api.multi
    def set_of_date_purchase_order_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'purchase.config.settings', 'of_date_purchase_order', self.of_date_purchase_order)

    @api.multi
    def set_of_tax_mandatory(self):
        for view in (
            self.env.ref('of_purchase.of_purchase_order_form_tax_required'),
            self.env.ref('of_purchase.of_invoice_supplier_form_tax_required'),
        ):
            if view:
                view.write({'active': self.of_tax_mandatory})
        return self.env['ir.values'].sudo().set_default(
            'purchase.config.settings', 'of_tax_mandatory',
            self.of_tax_mandatory)
