# -*- coding: utf-8 -*-

from odoo import models, fields, api

import os
import base64
import tempfile

try:
    import pyPdf
except ImportError:
    pyPdf = None

try:
    import pypdftk
except ImportError:
    pypdftk = None

class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

    of_total_cout = fields.Monetary(compute='_compute_of_marge', string='Marge')
    of_marge = fields.Monetary(compute='_compute_of_marge', string='Marge')
    of_marge_pc = fields.Float(compute='_compute_of_marge', string='Marge %')

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

    @api.depends('order_line', 'amount_untaxed')
    def _compute_of_marge(self):
        for order in self:
            cout = 0.0
            for line in order.order_line:
                cout += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom) * line.product_uom_qty
            # Il n'est pas nécessaire de faire des arrondis (parce que je l'ai décidé)
            order.of_total_cout = cout
            order.of_marge = order.amount_untaxed - cout
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

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_unit = fields.Float(digits=False)

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
    def set_of_deposit_product_categ_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_deposit_product_categ_id_setting', self.of_deposit_product_categ_id_setting.id)
