# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare
import os
import base64
import tempfile
import itertools
import json

try:
    import pyPdf
except ImportError:
    pyPdf = None

try:
    import pypdftk
except ImportError:
    pypdftk = None

NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def pdf_afficher_multi_echeances(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_afficher_multi_echeances')

    def pdf_afficher_nom_parent(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_nom_parent')

    def pdf_afficher_civilite(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_civilite')

    def pdf_afficher_telephone(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_telephone')

    def pdf_afficher_mobile(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_mobile')

    def pdf_afficher_fax(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_fax')

    def pdf_afficher_email(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_email')

    def pdf_afficher_date_validite(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_date_validite_devis')

    def get_color_section(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'of_color_bg_section')

    def _search_of_to_invoice(self, operator, value):
        # Récupération des bons de commande non entièrement livrés
        self._cr.execute("SELECT DISTINCT order_id\n"
                         "FROM sale_order_line\n"
                         "WHERE qty_to_invoice + qty_invoiced < product_uom_qty")
        order_ids = self._cr.fetchall()

        domain = ['&',
                  ('state', 'in', ('sale', 'done')),
                  ('order_line.qty_to_invoice', '>', 0)]
        if order_ids:
            domain = ['&'] + domain + [('id', 'not in', zip(*order_ids)[0])]
        return domain

    of_to_invoice = fields.Boolean(u"Entièrement facturable", compute='_compute_of_to_invoice', search='_search_of_to_invoice')
    of_notes_facture = fields.Html(string="Notes facture", oldname="of_notes_factures")
    of_notes_intervention = fields.Html(string="Notes intervention")
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)
    of_mail_template_ids = fields.Many2many("of.mail.template", string=u"Insérer documents", help=u"Intégrer des documents pdf au devis/bon de commande (exemple : CGV)")

    of_total_cout = fields.Monetary(compute='_compute_of_marge', string='Prix de revient')
    of_marge_pc = fields.Float(compute='_compute_of_marge', string='Marge %')

    of_etiquette_partenaire_ids = fields.Many2many('res.partner.category', related='partner_id.category_id', string=u"Étiquettes client")
    of_client_view = fields.Boolean(string='Vue client/vendeur')

    of_date_vt = fields.Date(string="Date visite technique", help=u"Si renseignée apparaîtra sur le devis / Bon de commande")

    of_echeance_line_ids = fields.One2many('of.sale.echeance', 'order_id', string=u"Échéances")

    of_echeances_modified = fields.Boolean(u"Les échéances ont besoin d'être recalculées", compute="_compute_of_echeances_modified")

    @api.depends('of_echeance_line_ids', 'amount_total')
    def _compute_of_echeances_modified(self):
        for order in self:
            order.of_echeances_modified = bool(order.of_echeance_line_ids and
                                               float_compare(order.amount_total,
                                                             sum(order.of_echeance_line_ids.mapped('amount')),
                                                             precision_rounding=.01))

    @api.multi
    def _of_compute_echeances(self):
        self.ensure_one()
        if not self.payment_term_id:
            return False
        dates = {
            'order': self.state not in ('draft', 'sent', 'cancel') and self.confirmation_date,
            'invoice': self.invoice_status == 'invoiced' and self.invoice_ids[0].date_invoice,
            'default': False,
        }
        amounts = self.payment_term_id.compute(self.amount_total, dates=dates)[0]

        amount_total = self.amount_total
        pct_left = 100.0
        pct = 0
        result = [(5, )]
        for term, (date, amount) in itertools.izip(self.payment_term_id.line_ids, amounts):
            pct_left -= pct
            pct = round(100 * amount / amount_total, 2) if amount_total else 0

            line_vals = {
                'name': term.name,
                'percent': pct,
                'amount': amount,
                'date': date,
            }
            result.append((0, 0, line_vals))
        if len(result) > 1:
            result[-1][2]['percent'] = pct_left
        return result

    @api.onchange('payment_term_id')
    def _onchange_payment_term_id(self):
        if self.payment_term_id:
            self.of_echeance_line_ids = self._of_compute_echeances()

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        self._onchange_payment_term_id()

    @api.multi
    def of_update_dates_echeancier(self):
        for order in self:
            if not order.payment_term_id:
                continue

            dates = {
                'order': order.confirmation_date,
                'invoice': order.invoice_status == 'invoiced' and order.invoice_ids[0].date_invoice,
                'default': False,
            }
            force_dates = [echeance.date for echeance in order.of_echeance_line_ids]
            echeances = order.payment_term_id.compute(order.amount_total, dates=dates, force_dates=force_dates)[0]

            if len(echeances) != len(order.of_echeance_line_ids):
                continue

            for echeance, ech_calc in itertools.izip(order.of_echeance_line_ids, echeances):
                if ech_calc[0] and not echeance.date:
                    echeance.date = ech_calc[0]

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        self.of_update_dates_echeancier()
        return True

    @api.multi
    def of_recompute_echeance_last(self):
        for order in self:
            if not order.of_echeance_line_ids:
                continue

            percent = 100.0
            amount = order.amount_total
            for echeance in order.of_echeance_line_ids:
                if echeance.last:
                    echeance.write({
                        'percent': percent,
                        'amount': amount,
                    })
                else:
                    percent -= echeance.percent
                    amount -= echeance.amount

    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        # Recalcul de la dernière échéance si besoin
        self.filtered('of_echeances_modified').of_recompute_echeance_last()
        return res

    @api.depends('state', 'order_line', 'order_line.qty_to_invoice', 'order_line.product_uom_qty')
    def _compute_of_to_invoice(self):
        for order in self:
            if order.state not in ('sale', 'done'):
                order.of_to_invoice = False
            for line in order.order_line:
                if line.qty_to_invoice + line.qty_invoiced < line.product_uom_qty:
                    order.of_to_invoice = False
                    break
            else:
                order.of_to_invoice = True

    @api.depends('margin', 'amount_untaxed')
    def _compute_of_marge(self):
        for order in self:
            cout = order.amount_untaxed - order.margin
            order.of_total_cout = cout
            order.of_marge_pc = 100 * (1 - cout / order.amount_untaxed) if order.amount_untaxed else -100

    @api.multi
    def _detect_doc_joint(self):
        """
        Cette fonction retourne les données des documents à joindre au fichier pdf du devis/commande au format binaire.
        Le document retourné correspond au fichier pdf joint au modéle de courrier.
        @todo: Permettre l'utilisation de courriers classiques et le remplissage des champs.
        """
        self.ensure_one()
        data = []
        for mail_template in self.of_mail_template_ids:
            if mail_template.file:
                # Utilisation des documents pdf fournis
                data.append(mail_template.file)
        return data

    def toggle_view(self):
        """ Permet de basculer entre la vue vendeur/client
        """
        self.of_client_view = not self.of_client_view

class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        if report_name in ('sale.report_saleorder',):
            # On ajoute au besoin les documents joint
            order = self.env['sale.order'].browse(docids)[0]
            for mail_data in order._detect_doc_joint():
                if mail_data:
                    # Create temp files
                    fd1, order_pdf = tempfile.mkstemp()
                    fd2, mail_pdf = tempfile.mkstemp()
                    fd3, merge_pdf = tempfile.mkstemp()

                    os.write(fd1, result)
                    os.write(fd2, base64.b64decode(mail_data))

                    output = pyPdf.PdfFileWriter()
                    pdfOne = pyPdf.PdfFileReader(file(order_pdf, "rb"))
                    pdfTwo = pyPdf.PdfFileReader(file(mail_pdf, "rb"))

                    for page in range(pdfOne.getNumPages()):
                        output.addPage(pdfOne.getPage(page))

                    for page in range(pdfTwo.getNumPages()):
                        output.addPage(pdfTwo.getPage(page))

                    outputStream = file(merge_pdf, "wb")
                    output.write(outputStream)
                    outputStream.close()

                    result = file(merge_pdf, "rb").read()
        return result


class OFInvoiceReportTotalGroup(models.Model):
    _inherit = 'of.invoice.report.total.group'
    _description = "Impression des totaux de factures et commandes de vente"

    @api.multi
    def filter_lines(self, lines):
        self.ensure_one()
        if not self.is_group_paiements():
            return super(OFInvoiceReportTotalGroup, self).filter_lines(lines)
        # Retour des lignes dont l'article correspond à un groupe de rapport de facture
        #   et dont la ligne de commande associée a une date antérieure
        #   (seul un paiement d'une facture antérieure doit figurer sur une facture)
        lines = lines.filtered(lambda l: ((l.product_id in self.product_ids or
                                           l.product_id.categ_id in self.categ_ids) and
                                          l.sale_line_ids and l.sale_line_ids[0].create_date < l.create_date))
        # Si une facture d'acompte possède plusieurs lignes, il est impératif de les gérer de la même façon
        invoices = lines.mapped('invoice_id')
        sale_lines = lines.mapped('sale_line_ids')
        for sale_line in sale_lines:
            sale_line_invoices = sale_line.invoice_lines.mapped('invoice_id')
            for sale_line2 in sale_line.order_id.order_line:
                if sale_line2 != sale_line and sale_line2.invoice_lines.mapped('invoice_id') == sale_line_invoices:
                    lines |= sale_line2.invoice_lines.filtered(lambda l: l.invoice_id in invoices)
        return lines


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_unit = fields.Float(digits=False)
    of_client_view = fields.Boolean(string="Vue client/vendeur", related="order_id.of_client_view")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        afficher_descr_fab = self.env.user.company_id.afficher_descr_fab
        afficher = afficher_descr_fab == 'devis' or afficher_descr_fab == 'devis_factures'
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
        )
        if product and product.description_fabricant and afficher:
            name = self.name
            name += '\n' + product.description_fabricant
            self.update({'name': name})
        return res

    def of_get_line_name(self):
        self.ensure_one()
        # inhiber l'affichage de la référence
        afficher_ref = self.env['ir.values'].get_default('sale.config.settings', 'pdf_display_product_ref_setting')
        le_self = self.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
        )
        name = le_self.name
        if not afficher_ref:
            if name.startswith("["):
                splitted = name.split("]")
                if len(splitted) > 1:
                    splitted.pop(0)
                    name = ']'.join(splitted).strip()
        return name.split("\n")  # utilisation t-foreach dans template qweb

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    price_unit = fields.Float(digits=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        afficher_descr_fab = self.env.user.company_id.afficher_descr_fab
        afficher = afficher_descr_fab == 'factures' or afficher_descr_fab == 'devis_factures'
        product = self.product_id.with_context(
            lang=self.invoice_id.partner_id.lang,
            partner=self.invoice_id.partner_id.id,
        )
        if product and product.description_fabricant and afficher:
            self.name += '\n' + product.description_fabricant
        return res

class Company(models.Model):
    _inherit = 'res.company'

    afficher_descr_fab = fields.Selection(
        [
            ('non', 'Ne pas afficher'),
            ('devis', 'Dans les devis'),
            ('factures', 'Dans les factures'),
            ('devis_factures', 'Dans les devis et les factures'),
        ], string="afficher descr. fabricant", default='devis_factures',
        help="La description du fabricant d'un article sera ajoutée à la description de l'article dans les documents."
    )

class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_deposit_product_categ_id_setting = fields.Many2one(
        'product.category',
        string=u"(OF) Catégorie des acomptes",
        help=u"Catégorie des articles utilisés pour les acomptes")

    stock_warning_setting = fields.Boolean(
        string="(OF) Stock", required=True, default=False,
        help="Afficher les messages d'avertissement de stock ?")

    pdf_display_product_ref_setting = fields.Boolean(
        string="(OF) Réf. produits", required=True, default=False,
        help="Afficher les références produits dans les rapports PDF ?")

    pdf_date_validite_devis = fields.Boolean(
        string="(OF) Date validité devis", required=True, default=False,
        help="Afficher la date de validité dans le rapport PDF des devis ?")

    pdf_adresse_nom_parent = fields.Boolean(
        string=u"(OF) Nom parent contact", required=True, default=False,
        help=u"Afficher le nom du 'parent' du contact au lieu du nom du contact dans les rapport PDF ?")
    pdf_adresse_civilite = fields.Boolean(
        string=u"(OF) Civilités", required=True, default=False,
        help=u"Afficher la civilité dans les rapport PDF ?")
    pdf_adresse_telephone = fields.Boolean(
        string=u"(OF) Téléphone", required=True, default=False,
        help=u"Afficher le numéro de téléphone dans les rapport PDF ?")
    pdf_adresse_mobile = fields.Boolean(
        string=u"(OF) Mobile", required=True, default=False,
        help=u"Afficher le numéro de téléphone mobile dans les rapport PDF ?")
    pdf_adresse_fax = fields.Boolean(
        string="(OF) Fax", required=True, default=False,
        help=u"Afficher le fax dans les rapport PDF ?")
    pdf_adresse_email = fields.Boolean(
        string="(OF) E-mail", required=True, default=False,
        help=u"Afficher l'adresse email dans les rapport PDF ?")
    pdf_afficher_multi_echeances = fields.Boolean(
        string="(OF) Multi-échéances", required=True, default=False,
        help="Afficher les échéances multiples dans les rapports PDF ?")
    of_color_bg_section = fields.Char(
        string="(OF) Couleur fond titres section",
        help=u"Choisissez un couleur de fond pour les titres de section", default="#F0F0F0")

    @api.multi
    def set_pdf_adresse_nom_parent_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_nom_parent', self.pdf_adresse_nom_parent)

    @api.multi
    def set_pdf_adresse_civilite_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_civilite', self.pdf_adresse_civilite)

    @api.multi
    def set_pdf_adresse_telephone_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_telephone', self.pdf_adresse_telephone)

    @api.multi
    def set_pdf_adresse_mobile_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_mobile', self.pdf_adresse_mobile)

    @api.multi
    def set_pdf_adresse_fax_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_fax', self.pdf_adresse_fax)

    @api.multi
    def set_pdf_adresse_email_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_email', self.pdf_adresse_email)

    @api.multi
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'stock_warning_setting', self.stock_warning_setting)

    @api.multi
    def set_pdf_display_product_ref_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_display_product_ref_setting', self.pdf_display_product_ref_setting)

    @api.multi
    def set_pdf_date_validite_devis_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_date_validite_devis', self.pdf_date_validite_devis)

    @api.multi
    def set_of_deposit_product_categ_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_deposit_product_categ_id_setting', self.of_deposit_product_categ_id_setting.id)

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_color_bg_section', self.of_color_bg_section)

    @api.multi
    def set_pdf_afficher_multi_echeances_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_afficher_multi_echeances', self.pdf_afficher_multi_echeances)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_date_vt = fields.Date(string="Date visite technique")
    of_sale_order_ids = fields.Many2many('sale.order', compute="_compute_of_sale_order_ids", string="Bons de commande")
    of_residual = fields.Float(string=u"Somme du montant non payé des factures d'acompte et de la facture finale", compute="_compute_of_residual")
    of_residual_equal = fields.Boolean(compute="_compute_of_residual")

    def _compute_of_sale_order_ids(self):
        for invoice in self:
            invoice.of_sale_order_ids = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')

    def _compute_of_residual(self):
        group_paiements = self.env['of.invoice.report.total.group'].get_group_paiements()
        if not group_paiements.invoice:
            # Si le groupe des paiements est désactivé on ne gère pas les acomptes
            group_paiements = group_paiements.browse([])
        products = group_paiements.product_ids
        if group_paiements.categ_ids:
            products |= self.env['product.product'].search([('categ_id', 'in', group_paiements.categ_ids._ids)])
        if not products:
            for invoice in self:
                invoice.of_residual = invoice.residual
                invoice.of_residual_equal = True
            return
        for invoice in self:
            lines = invoice.invoice_line_ids.filtered(lambda l: l.product_id in products)
            if not lines:
                invoice.of_residual = invoice.residual
                invoice.of_residual_equal = True
                continue
            order_lines = lines.mapped('sale_line_ids')
            invoices = invoice | order_lines.mapped('invoice_lines').mapped('invoice_id')
            invoice.of_residual = sum(invoices.mapped('residual'))
            invoice.of_residual_equal = invoice.state == 'draft' or float_compare(invoice.of_residual, invoice.residual, 2) == 0

    def get_color_section(self):
        return self.env['ir.values'].get_default('account.config.settings', 'of_color_bg_section')

    @api.multi
    def action_invoice_open(self):
        """Mise à jour des dates de l'échéancier"""
        res = super(AccountInvoice, self).action_invoice_open()
        acompte_categ_id = self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting')
        lines = self.mapped('invoice_line_ids').filtered(lambda line: line.product_id.categ_id.id != acompte_categ_id)
        orders = lines.mapped('sale_line_ids').mapped('order_id')
        orders.of_update_dates_echeancier()
        return res

    @api.multi
    def _of_get_linked_invoices(self, lines):
        """ [IMPRESSION]
        Retourne les factures liées à la facture courante.
        Les factures liées sont celles dont une ligne est liée à la même ligne de commande qu'une ligne de lines.
        Toute facture liée à une facture liée est également retournée.
        @param lines : Lignes de la facture courante sur lesquelles le lien est déterminé
        """
        invoices = self
        to_check = lines.mapped('sale_line_ids').mapped('invoice_lines').mapped('invoice_id')
        while to_check:
            invoices |= to_check
            to_check = (to_check
                        .mapped('invoice_line_ids')
                        .mapped('sale_line_ids')
                        .mapped('invoice_lines')
                        .mapped('invoice_id')) - invoices
        return invoices

    @api.multi
    def _of_get_printable_payments(self, lines):
        """ [IMPRESSION]
        Renvoie les lignes à afficher.
        """
        account_move_line_obj = self.env['account.move.line']
        # Liste des factures et factures d'acompte
        invoices = self._of_get_linked_invoices(lines)

        # Retour de tous les paiements des factures
        # On distingue les paiements de la facture principale de ceux des factures liées
        result_dict = {}
        for invoice in invoices:
            widget = json.loads(invoice.payments_widget.replace("'", "\'"))
            if not widget:
                continue
            for payment in widget.get('content', []):
                # Les paiements sont classé dans l'ordre chronologique
                sort_key = (payment['date'], invoice.date_invoice, invoice.number, payment['payment_id'])

                move_line = account_move_line_obj.browse(payment['payment_id'])
                name = self._of_get_payment_display(move_line)
                result_dict[sort_key] = (name, payment['amount'])
        result = [result_dict[key] for key in sorted(result_dict)]
        return result

    @api.multi
    def order_lines_layouted(self):
        """
        Retire les lignes de facture qui doivent êtres affichées dans les totaux.
        """
        report_pages_full = super(AccountInvoice, self).order_lines_layouted()
        report_lines = self._of_get_printable_lines()
        report_pages = []
        for page_full in report_pages_full:
            page = []
            for group in page_full:
                lines = [line for line in group['lines'] if line in report_lines]
                if lines:
                    group['lines'] = lines
                    page.append(group)
            if page:
                report_pages.append(page)
        return report_pages


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    of_color_bg_section = fields.Char(string="(OF) Couleur fond titres section", help=u"Choisissez un couleur de fond pour les titres de section", default="#F0F0F0")

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_color_bg_section', self.of_color_bg_section)

class OFSaleEcheance(models.Model):
    _name = "of.sale.echeance"
    _order = "order_id, sequence, id"

    name = fields.Char(string="Nom", required=True, default=u"Échéance")
    order_id = fields.Many2one("sale.order", string="Commande")
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)  # TODO ADAPT SALE
    amount = fields.Monetary(string="Montant", currency_field='currency_id')
    percent = fields.Float(string=u"Pourcentage", digits=dp.get_precision('Product Price'))
    last = fields.Boolean(string="Dernière Échéance", compute="_compute_last")

    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of payment term lines.")
    date = fields.Date(string='Date')

    @api.multi
    def _compute_last(self):
        for order in self.mapped('order_id'):
            for echeance in order.of_echeance_line_ids:
                echeance.last = echeance == order.of_echeance_line_ids[-1]

    @api.onchange("amount")
    def _onchange_amount(self):
        """Met à jour le pourcentage en fonction du montant"""
        order_amount = self._context.get('order_amount', self.order_id.amount_total)
        # Test: si le nouveau montant est calculé depuis le pourcentage, on ne le recalcule pas
        test_amount = order_amount * self.percent / 100
        if float_compare(self.amount, test_amount, precision_rounding=.01):
            self.percent = self.amount * 100 / order_amount if order_amount else 0

    @api.onchange("percent")
    def _onchange_percent(self):
        """Met à jour le montant en fonction du pourcentage"""
        order_amount = self._context.get('order_amount', self.order_id.amount_total)
        # Test: si le nouveau pourcentage est calculé depuis le montant, on ne le recalcule pas
        test_percent = self.amount * 100 / order_amount if order_amount else 0
        if float_compare(self.percent, test_percent, precision_rounding=.01):
            self.amount = order_amount * self.percent / 100

class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    @api.model
    def _get_of_option_date(self):
        result = super(AccountPaymentTermLine, self)._get_of_option_date()
        for i in xrange(len(result)):
            if result[i][0] == 'invoice':
                i += 1
                break
        return result[:i] + [('order', 'Date de commande')] + result[i:]
