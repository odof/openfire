# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def of_get_line_name(self):
        self.ensure_one()
        # inhiber l'affichage de la référence
        afficher_ref = self.env['ir.values'].get_default('account.config.settings', 'pdf_display_product_ref')
        le_self = self.with_context(
            lang=self.invoice_id.partner_id.lang,
            partner=self.invoice_id.partner_id.id,
        )
        name = le_self.name
        if not afficher_ref:
            if name.startswith("["):
                splitted = name.split("]")
                if len(splitted) > 1:
                    splitted.pop(0)
                    name = ']'.join(splitted).strip()
        return name.split("\n")  # utilisation t-foreach dans template qweb


class OFInvoiceReportTotalGroup(models.Model):
    _name = 'of.invoice.report.total.group'
    _description = "Impression des totaux de factures de vente"
    _order = 'position, sequence'

    name = fields.Char(string='Nom')
    subtotal_name = fields.Char(string="Libellé du sous-total")
    sequence = fields.Integer(string=u"Séquence", default=10)
    product_ids = fields.Many2many('product.product', string="Filtre sur articles")
    categ_ids = fields.Many2many('product.category', string=u"Filtre sur catégories")
    invoice = fields.Boolean(string='Concerne les factures', default=True)
    order = fields.Boolean(
        string='Concerne les commandes clients',
        readonly=False)
    position = fields.Selection(
        [('0-ht', "Hors taxe"), ('1-ttc', "TTC")],
        string=u"Afficher dans les montants", required=True, default='1-ttc')
    hide_amount_total = fields.Boolean(string=u"Cacher le montant TTC")

    @api.model
    def get_group_paiements(self):
        return self.env.ref('of_account_invoice_report.of_invoice_report_total_group_paiements')

    @api.multi
    def is_group_paiements(self):
        return self == self.get_group_paiements()

    @api.multi
    def filter_lines(self, lines, invoices=None):
        """
        Filtre les lignes reçues en fonction des articles/catégories autorisés pour le groupe courant.
        """
        self.ensure_one()
        if self.is_group_paiements():
            # On n'autorise pas d'articles dans les paiements. (Voir module of_sale pour cette possibilité)
            return False
        if self.position == '1-ttc':
            # On n'autorise pas de ligne avec un montant de taxe dans les groupes ttc.
            lines = lines.filtered(lambda l: float_compare(l.price_subtotal, l.price_total, 2) == 0)
        return lines.filtered(lambda l: (l.product_id in self.product_ids or
                                         l.product_id.categ_id in self.categ_ids)) or False
