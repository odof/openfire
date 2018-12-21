# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.misc import formatLang
import json
from odoo.tools import float_is_zero
from odoo.tools.translate import _

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    # Note : les fonctions de cette classe qui possèdent [IMPRESSION] dans leur description
    # ne sont appelées que lors de l'impression.

    of_amount_untaxed_without_advance = fields.Float(compute="_compute_amounts_order", string="Montant total HT des acomptes de la facture")
    of_amount_total_without_advance = fields.Float(compute="_compute_amounts_order", string="Montant total TTC des acomptes de la facture")
    of_acomptes_payments_widget = fields.Text(compute="_compute_acomptes_widget")
    of_residual = fields.Float(string=u"Somme du montant non payé des factures d'acompte et de la facture finale", compute="_compute_acomptes_widget")
    of_equal = fields.Boolean(compute="_compute_equal")

    @api.depends("of_residual", "residual", "state")
    def _compute_equal(self):
        """Renvoi vrai si le montant payé des factures d'acompte est égal au montant de la facture.
        Objectif : signaler que des factures d'acompte n'ont probablement pas été totalement payées."""
        for invoice in self:
            if invoice.state == 'draft':
                invoice.of_equal = True
            elif round(invoice.of_residual, 2) != round(invoice.residual, 2):
                invoice.of_equal = False
            elif round(invoice.of_residual, 2) == round(invoice.residual, 2):
                invoice.of_equal = True

    @api.depends('invoice_line_ids')
    def _compute_amounts_order(self):
        for invoice in self:
            lines = invoice.invoice_line_ids.filtered(lambda line: line.product_id.categ_id.id != self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting'))
            if not lines:
                lines = invoice.invoice_line_ids
                invoice.of_amount_untaxed_without_advance = sum([line.price_subtotal for line in invoice.invoice_line_ids])
            else:
                invoice.of_amount_untaxed_without_advance = sum([line.price_subtotal for line in lines])
            invoice.of_amount_total_without_advance = invoice.of_amount_untaxed_without_advance
            for line in lines:
                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
                for tax in taxes:
                    val = self._prepare_tax_line_vals(line, tax)
                    invoice.of_amount_total_without_advance += val['amount']

    @api.multi
    def _get_widgets(self, invoice, replace=False):
        """ Renvoi le ou les widgets des paiements des factures d'acompte et le montant lettré des paiements.
        Ajoute également un boolean nommé 'replace' dans le widget pour permettre un affichage différent au niveau
        de l'impression (affichage nom de la facture ou lieu de la date de paiement).
        """

        if not invoice.payments_widget:
            return {}, 0
        json_acceptable_string = invoice.payments_widget.replace("'", "\"")
        widget = json.loads(json_acceptable_string)
        total = 0
        if isinstance(widget, dict) and 'content' in widget:
            for payment in widget["content"]:
                payment["replace"] = replace
                payment["name"] = invoice.number
                total += payment["amount"]
        return widget, total

    @api.depends('invoice_line_ids')
    def _compute_acomptes_widget(self):
        """ Fonction permettant de récupérer les widgets des paiements des factures d'acomptes
        ainsi que le montant dû de la commande.
        """

        order_line_obj = self.env['sale.order.line']
        for invoice in self:
            widget = {}
            total = invoice.of_amount_total_without_advance
            lines = invoice.invoice_line_ids.filtered(lambda line: line.product_id.categ_id.id == self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting'))
            if lines != invoice.invoice_line_ids:
                for line in lines:
                    order_line = order_line_obj.search([('invoice_lines', 'in', [line.id])])
                    invoice_lines = order_line.invoice_lines.filtered(lambda l: l.id != line.id)
                    if "content" not in widget:
                        widget, amount = invoice._get_widgets(invoice_lines.invoice_id, True)
                        total -= amount
                    else:
                        tmpwidget, amount = invoice._get_widgets(invoice_lines.invoice_id, True)
                        total -= amount
                        if "content" in tmpwidget:
                            widget["content"] += tmpwidget["content"]
                invoice.of_acomptes_payments_widget = json.dumps(widget)
            else:
                invoice.of_acomptes_payments_widget = False
            widget, amount = invoice._get_widgets(self)
            invoice.of_residual = total - amount

    @api.multi
    def _get_payments_and_acomptes(self):
        """ [IMPRESSION]
        Permet de récupérer tous les widgets des paiements (champ payments_widget)
        """
        if self.env['ir.values'].get_default('account.config.settings', 'of_impression_acomptes') != 'as_payment':
            return json.loads(self.payments_widget)
        res = {"content": []}
        # Chargement des payments_widget des factures d'acomptes
        tmpwidget = False
        if self.of_acomptes_payments_widget:
            tmpwidget = json.loads(self.of_acomptes_payments_widget.replace("'", "\""))
        if tmpwidget:
            res["content"] += tmpwidget["content"]
        # Chargement des payments_widget de la facture
        if self.payments_widget:
            tmpwidget = json.loads(self.payments_widget.replace("'", "\""))
        if tmpwidget:
            res["content"] += tmpwidget["content"]
        if not res["content"]:
            return False
        return res

    @api.multi
    def _get_printable_lines(self, lines):
        """ [IMPRESSION]
        Renvoi les lignes à afficher
        """
        if self.env['ir.values'].get_default('account.config.settings', 'of_impression_acomptes') != 'as_payment':
            return lines
        lines_to_remove = self.invoice_line_ids.filtered(lambda line: line.product_id.categ_id.id == self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting'))
        if self.invoice_line_ids == lines_to_remove:  # Pour fonctionner avec les sections on doit faire la vérification sur toutes les lignes de la facture.
            return lines
        for line_to_remove in lines_to_remove:
            if line_to_remove in lines:
                lines.remove(line_to_remove)
        return lines

    @api.multi
    def order_lines_layouted(self):
        """ [IMPRESSION]
        Permet de n'afficher que les sections des lignes de facture qui ont d'autres articles que les articles d'acompte
        sauf si il n'y a que des articles d'acompte sur la facture (exemple : ne pas laisser une section vide).
        """
        report_pages = super(AccountInvoice, self).order_lines_layouted()
        if self.env['ir.values'].get_default('account.config.settings', 'of_impression_acomptes') != 'as_payment':
            return report_pages
        lines_to_remove = self.invoice_line_ids.filtered(lambda line: line.product_id.categ_id.id == self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting'))
        if self.invoice_line_ids == lines_to_remove:
            return report_pages
        for page in report_pages:
            for layout_category in page:
                lines = layout_category.get("lines", [])
                for line_to_remove in lines_to_remove:
                    if line_to_remove in lines:
                        lines.remove(line_to_remove)
                if not lines:
                    page.remove(layout_category)
            if not page:
                report_pages.remove(page)
        return report_pages

    @api.multi
    def _get_tax_amount_by_group(self):
        """Récupère la liste des taxes par groupe pour lorsque l'option afficher l'acompte en pied de facture, le prendre comme un paiement et alors ne pas inclure la TVA."""
        if self.env['ir.values'].get_default('account.config.settings', 'of_impression_acomptes') != 'as_payment':
            return super(AccountInvoice, self)._get_tax_amount_by_group()
        return self._get_abs_taxes_values()

    @api.multi
    def _get_abs_taxes_values(self):
        """ [IMPRESSION]
        Permet de récupérer la valeur des différentes taxes sans inclure les acomptes.
        """
        res = {}
        tax_obj = self.env['account.tax']
        currency = self.currency_id or self.company_id.currency_id
        lines = self.invoice_line_ids.filtered(lambda line: line.product_id.categ_id.id != self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting'))
        if not lines:
            lines = self.invoice_line_ids
        for line in lines:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                tax_browse =  tax_obj.browse([tax['id']])
                res.setdefault(tax_browse.tax_group_id, 0.0)
                val = self._prepare_tax_line_vals(line, tax)
                res[tax_browse.tax_group_id] += abs(val['amount'])
        res = sorted(res.items(), key=lambda l: l[0].sequence)
        res = [(
            r[0].name, r[1], formatLang(self.with_context(lang=self.partner_id.lang).env, r[1], currency_obj=currency)
        ) for r in res]
        return res

    @api.multi
    def _acomptes_as_payments(self):
        if self.env['ir.values'].get_default('account.config.settings', 'of_impression_acomptes') == 'as_payment':
            return True
        return False

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    of_impression_acomptes = fields.Selection(
        [('as_payment', u"Faire apparaître les paiements des factures d'acompte avec les paiements de la facture finale"),
         ('line', u"Faire apparaître les lignes d'acompte avec les articles")], string=u"(OF) Acomptes",
        help=u"Si les acomptes apparaissent comme des paiements alors le total HT, la TVA, le total de la TVA et montant dû seront en fonction des montants de la commande et non ceux de la facture.",
        default='line',
        required=True)

    @api.multi
    def set_of_impression_acomptes_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_impression_acomptes', self.of_impression_acomptes)
