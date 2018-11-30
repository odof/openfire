# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
import os
import base64
import tempfile
from dateutil.relativedelta import relativedelta

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

    # TOD FIXME
    #def _default_line_ids(self):
    #    return [(0, 0, {'value': 'balance', 'percent': 100.0, 'sequence': 9, 'days': 0, 'option': 'day_after_invoice_date'})]

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

    echeance_line_ids = fields.One2many("of.sale.echeance", "order_id", string="Échéances",
                                        readonly=True, states={'draft': [('readonly', False)]})
    echeance_last_amount = fields.Monetary("Montant derniere echeance", currency_field="currency_id", digits=dp.get_precision('Product Price'))
    echeance_last_percent = fields.Float("Pourcentage derniere echeance", digits=dp.get_precision('Product Price'))
    echeance_last_a_jour =  fields.Boolean(u"echeance_last_a_jour",default=True)
    onchange_esc = fields.Boolean("for _onchange_echeance_line_ids")

    @api.onchange("echeance_last_a_jour")
    def _onchange_echeance_last_a_jour(self):
        """Met a jour la derniere ligne d'échéance"""
        if self.onchange_esc or not self.echeance_line_ids:
            self.onchange_esc = False
            self.echeance_last_a_jour = True
            return
        echeances = self.echeance_line_ids
        for echeance in echeances[:-1]:
            if echeance.percent and not echeance.amount: # affecter un montant
                echeance.amount = self.amount_total * echeance.percent / 100
            elif echeance.amount and not echeance.percent: # affecter un pourcentage
                echeance.percent = echeance.amount * 100 / self.amount_total
            elif type(echeance.id) is not int: # le nouveau record a un montant et un pourcentage -> le pourcentage prévaut
                echeance.amount = self.amount_total * echeance.percent / 100
        last_echeance_old = echeances[-1]
        last_echeance_old.percent =  100 - sum(echeances[:-1].mapped('percent'))
        last_echeance_old.amount = self.amount_total - sum(echeances[:-1].mapped('amount'))
        echeances_sorted = sorted(self.echeance_line_ids, key=lambda k: k['sequence'])
        last_echeance = echeances_sorted[-1]
        if self.echeance_last_a_jour:# and last_echeance and (last_echeance.percent != self.echeance_last_percent or last_echeance.amount != self.echeance_last_amount):
            vals = {"onchange_esc": True}
            lines_to_add = [(5,0,0)]
            pct_left = 100
            amt_left = self.amount_total
            for echeance in echeances_sorted[:-1]:
                pct_left -= echeance.percent or echeance.amount * 100 / self.amount_total
                amt_left -= echeance.amount or self.amount_total * echeance.percent / 100
                line_vals = {
                    "name": echeance.name,
                    "days": echeance.days,
                    "option": echeance.option,
                    "percent": echeance.percent,
                    "amount": echeance.amount,
                    #"last": echeance.last,
                    #"invoice_id": echeance.invoice_id.id,
                }
                lines_to_add.append((0,0,line_vals))
            if amt_left < 0 or pct_left < 0:
                self.echeance_last_a_jour = False
                raise UserError(u"La somme des pourcentages doit être égale à 100")
            last_vals = {
                "name": last_echeance.name,
                "days": last_echeance.days,
                "option": last_echeance.option,
                "percent": pct_left,
                "amount": amt_left,
                #"last": True,
                #"invoice_id": self.id,
            }
            lines_to_add.append((0,0,last_vals))
            vals["echeance_line_ids"] = lines_to_add
            vals["echeance_last_percent"] = pct_left
            vals["echeance_last_amount"] = amt_left
            self.update(vals)

    @api.onchange("payment_term_id")
    def _onchange_payment_term_id(self):
        if not self.payment_term_id:
            return
        else:
            pterm_lines = self.payment_term_id.line_ids
            pct_left = 100
            amt_left = self.amount_total
            vals = {"onchange_esc": True}
            lines_to_add = [(5,0,0)]
            for i in range(len(pterm_lines)):
                term = pterm_lines[i]
                if term.value == "percent":
                    pct = term.value_amount
                    amt = self.amount_total * pct / 100
                elif term.value == "fixed":
                    amt = term.value_amount
                    if self.amount_total == 0:
                        pct = 0
                    else:
                        pct = 100 * amt / self.amount_total
                else:
                    pct = pct_left
                    amt = amt_left
                pct_left -= pct
                amt_left -= amt
                last = term == pterm_lines[len(pterm_lines) - 1]
                line_vals = {
                    "name": term.name,
                    "days": term.days,
                    "percent": pct,
                    "amount": amt,
                    "option": term.option,
                    #"invoice_id": self.id,
                }
                lines_to_add.append((0,0,line_vals))
                if last:
                    vals["echeance_last_percent"] = pct
                    vals["echeance_last_amount"] = amt
                    vals["echeance_last_a_jour"] = True
            vals["echeance_line_ids"] = lines_to_add
            self.update(vals)

    @api.onchange("amount_total")
    def _onchange_amount_total(self):
        self.echeance_line_ids.compute_amount_from_percent()

    @api.onchange("echeance_line_ids")
    def _onchange_echeance_line_ids(self):
        if self.onchange_esc or not self.echeance_line_ids:
            self.onchange_esc = False
            self.echeance_last_a_jour = True
            return
        old_percent = self.echeance_last_percent
        new_percent = 100 - sum(self.echeance_line_ids[:-1].mapped('percent'))
        old_amount = self.echeance_last_amount
        new_amount = self.amount_total - sum(self.echeance_line_ids[:-1].mapped('amount'))
        #if old_amount != new_amount or old_percent != new_percent:
        self.update({"echeance_last_percent": new_percent,
                     "echeance_last_amount": new_amount,
                     "echeance_last_a_jour": False,
                     })
        if new_percent < 0 or new_amount < 0:
            raise UserError(u"Le pourcentage de la dernière ligne d'échéance doit être supérieur à zéro")

    @api.multi
    def recompute_echeances_values(self):
        """
        recalcule les echeances. retire les valeurs des nouvelles a l'ancienne derniere puis recalcule tout. a tester beaucoup ^^"
        """
        echeances = self.echeance_line_ids
        last_echeance = echeances[-1]
        nouvelles = self.env["of.sale.echeance"]
        anciennes = self.env["of.sale.echeance"]
        pcts_new = 0
        for echeance in echeances:
            if echeance.percent and not echeance.amount: # affecter un montant
                echeance.amount = self.amount_total * echeance.percent / 100
                nouvelles |= echeance
                pcts_new = echeance.percent
            elif echeance.amount and not echeance.percent: # affecter un pourcentage
                echeance.percent = echeance.amount * 100 / self.amount_total
                nouvelles |= echeance
                pcts_new = echeance.percent
            else:
                anciennes |= echeance
        last_old = anciennes[-1]
        last_old.percent -= pcts_new
        last_old.amount = self.amount_total * last_old.percent / 100
        if last_old.percent < 0 or last_old.amount < 0:
            self.echeance_last_a_jour = False
            raise UserError(u"La somme des pourcentages doit être égale à 100")

        pct_left = 100
        amt_left = self.amount_total
        for echeance in echeances[:-1]:
            if echeance.percent and not echeance.amount: # affecter un montant
                echeance.amount = self.amount_total * echeance.percent / 100
            elif echeance.amount and not echeance.percent: # affecter un pourcentage
                echeance.percent = echeance.amount * 100 / self.amount_total
            elif type(echeance.id) is not int: # le nouveau record a un montant et un pourcentage -> le pourcentage prévaut
                echeance.amount = self.amount_total * echeance.percent / 100
            pct_left -= echeance.percent
            amt_left -= echeance.amount
        vals = {"onchange_esc": False, "echeance_last_a_jour": True}
        if amt_left < 0 or pct_left < 0:
            self.echeance_last_a_jour = False
            raise UserError(u"La somme des pourcentages doit être égale à 100")
        last_vals = {
            "percent": pct_left,
            "amount": amt_left,
        }
        echeances[-1].write(last_vals)
        #self.echeance_line_ids.unlink()
        #lines_to_add.append((0,0,last_vals))
        #vals["echeance_line_ids"] = lines_to_add
        vals["echeance_last_percent"] = pct_left
        vals["echeance_last_amount"] = amt_left
        self.write(vals)

    @api.one
    def compute_echeances(self):
        date_ref = fields.Date.today()
        date_confirmation = self.confirmation_date or fields.Date.today()
        amount = self.amount_total
        sign = amount < 0 and -1 or 1
        result = []
        if self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        else:
            currency = self.env.user.company_id.currency_id
        prec = currency.decimal_places
        for line in self.echeance_line_ids:
            pct = line.percent
            amt = line.amount
            line_vals = {"amount": amt, "percent": pct, "name": line.name,}
            if amt:
                next_date = fields.Date.from_string(date_ref)
                if line.option == 'day_after_invoice_date':
                    next_date += relativedelta(days=line.days)
                elif line.option == 'fix_day_following_month':
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                elif line.option == 'last_day_following_month':
                    next_date += relativedelta(day=31, months=1)  # Getting last day of next month
                elif line.option == 'last_day_current_month':
                    next_date += relativedelta(day=31, months=0)  # Getting last day of next month
                elif line.option == 'day_after_order_date':
                    next_date = fields.Date.from_string(date_confirmation)
                    next_date += relativedelta(days=line.days)
                elif line.option == 'fix_day_following_order_month':
                    next_date = fields.Date.from_string(date_confirmation)
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                line_vals["date_deadline"] = fields.Date.to_string(next_date)
                result.append((0,0,line_vals))
        return result

    @api.multi
    def _prepare_invoice(self):
        #ajout de la date de la visite technique dans la vue formulaire de la facture
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_date_vt'] = self.of_date_vt
        invoice_vals["echeance_line_ids"] = self.compute_echeances()[0] #TODO comprendre pourquoi pourquoi le resultat de compute_echeances est encapsulé dans une liste
        return invoice_vals

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

    @api.multi
    def write(self,vals):
        super(SaleOrder,self).write(vals)
        if not vals.get("echeance_last_a_jour",True):
            for order in self:
                order.recompute_echeances_values()
        return True

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

    pdf_date_validite_devis = fields.Boolean(string="(OF) Date validité devis", required=True, default=False,
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
    pdf_afficher_multi_echeances = fields.Boolean(string="(OF) Multi-échéances", required=True, default=True,
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

    def get_color_section(self):
        return self.env['ir.values'].get_default('account.config.settings', 'of_color_bg_section')

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    of_color_bg_section = fields.Char(string="(OF) Couleur fond titres section", help=u"Choisissez un couleur de fond pour les titres de section", default="#F0F0F0")

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_color_bg_section', self.of_color_bg_section)

class OFSaleEcheance(models.Model):
    _name = "of.sale.echeance"
    _order = "order_id, sequence, id"

    #date_deadline = fields.Date(string=u"Échéance")
    name = fields.Char(string="Nom", required=True, default=u"Échéance")
    order_id = fields.Many2one("sale.order", string="Commande")
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)# TODO ADAPT SALE
    amount = fields.Monetary(string="Montant", currency_field='currency_id')
    percent = fields.Float(string=u"Pourcentage", digits=dp.get_precision('Product Price'))
    last = fields.Boolean(string="Dernière Échéance",compute="_compute_last")
    # booléen pour eviter la boucle infinie de onchange
    onchange_esc = fields.Boolean(string="for onchange")

    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of payment term lines.")
    days = fields.Integer(string='Number of Days', required=True, default=0)
    option = fields.Selection([
            ('day_after_invoice_date', 'Day(s) after the invoice date'),
            ('fix_day_following_month', 'Day(s) after the end of the invoice month (Net EOM)'),
            ('last_day_following_month', 'Last day of following month'),
            ('last_day_current_month', 'Last day of current month'),
            ('day_after_order_date', 'Day(s) after the confirmation date'),
            ('fix_day_following_order_month', 'Day(s) after the end of the order month (Net EOM)'),
        ],
        default='day_after_invoice_date', required=True, string='Options'
        )

    @api.multi
    def _compute_last(self):
        for order in self.mapped('order_id'):
            for echeance in order.echeance_line_ids:
                echeance.last = echeance == order.echeance_line_ids[-1]

    @api.multi
    def compute_amount_from_percent(self):
        u"""fonction appelée quand le montant total de la facture change, pour recalculer les montants"""
        for order in self.mapped("order_id"):
            for echeance in order.echeance_line_ids:
                vals = {"amount": order.amount_total * echeance.percent / 100,"onchange_esc":True}
                echeance.update(vals)

    @api.onchange("amount")
    def _onchange_amount(self):
        """Met a jour le pourcentage en fonction du montant"""
        self.ensure_one()
        if self.last:
            self.onchange_esc = False
            return
        old_percent = self.percent # supprimer ou mettre dans le if old_amount != new_amount
        if self.order_id.amount_total == 0:
            new_percent = False
        else:
            new_percent = self.amount * 100 / self.order_id.amount_total
        if not self.onchange_esc:
            vals = {"percent": new_percent,"onchange_esc":True}
            self.update(vals)
        else:
            self.onchange_esc = False

    @api.onchange("percent")
    def _onchange_percent(self):
        """Met a jour le montant en fonction du pourcentage"""
        self.ensure_one()
        if self.last:
            self.onchange_esc = False
            return
        old_amount = self.amount # supprimer ou mettre dans le if old_amount != new_amount
        new_amount = self.order_id.amount_total * self.percent / 100
        if not self.onchange_esc:
            vals = {"amount": new_amount,"onchange_esc":True}
            self.update(vals)
        else:
            self.onchange_esc = False

    @api.model
    def compute_last_values_order(self,order_id):
        """Met a jour la derniere échéance lors du write"""
        echeances = self.search([("order_id","=",order_id.id)],order="sequence,id")
        if not echeances:
            return
        last_echeance = echeances[-1]
        percent_left = 100
        montant_left = order_id.amount_total
        for i in range(0,len(echeances)-1):
            percent_left -= echeances[i].percent
            montant_left -= echeances[i].amount
        if percent_left < 0 or montant_left < 0:
            raise UserError("Incohérence de données. La somme des pourcentages des échéances doit être égale à 100")
        vals = {"amount": montant_left, "percent": percent_left}
        last_echeance.write(vals)

    """@api.multi
    def write(self,vals):
        super(OFSaleEcheance, self).write(vals)
        la_line = False
        if len(self) > 0:
            la_line = self[0]
        # mettre a jour percent et amount
        if la_line and not la_line.last and (vals.get("amount",False) or vals.get("percent",False)):
            self.env["of.sale.echeance"].compute_last_values_order(la_line.order_id)
            la_line.order_id.echeance_last_a_jour = True
        return True"""

class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    @api.one
    def compute(self, value, date_ref=False, date_ref_2=False):
        date_ref = date_ref or fields.Date.today()
        date_ref_2 = date_ref_2 or fields.Date.today()
        amount = value
        sign = value < 0 and -1 or 1
        result = []
        if self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        else:
            currency = self.env.user.company_id.currency_id
        prec = currency.decimal_places
        for line in self.line_ids:
            if line.value == 'fixed':
                amt = sign * round(line.value_amount, prec)
            elif line.value == 'percent':
                amt = round(value * (line.value_amount / 100.0), prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                next_date = fields.Date.from_string(date_ref)
                if line.option == 'day_after_invoice_date':
                    next_date += relativedelta(days=line.days)
                elif line.option == 'fix_day_following_month':
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                elif line.option == 'last_day_following_month':
                    next_date += relativedelta(day=31, months=1)  # Getting last day of next month
                elif line.option == 'last_day_current_month':
                    next_date += relativedelta(day=31, months=0)  # Getting last day of next month
                elif line.option == 'day_after_order_date':
                    next_date = fields.Date.from_string(date_ref_2)
                    next_date += relativedelta(days=line.days)
                elif line.option == 'fix_day_following_order_month':
                    next_date = fields.Date.from_string(date_ref_2)
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                result.append((fields.Date.to_string(next_date), amt))
                amount -= amt
        amount = reduce(lambda x, y: x + y[1], result, 0.0)
        dist = round(value - amount, prec)
        if dist:
            last_date = result and result[-1][0] or fields.Date.today()
            result.append((last_date, dist))
        return result

class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    option = fields.Selection([
            ('day_after_invoice_date', 'Day(s) after the invoice date'),
            ('fix_day_following_month', 'Day(s) after the end of the invoice month (Net EOM)'),
            ('last_day_following_month', 'Last day of following month'),
            ('last_day_current_month', 'Last day of current month'),
            ('day_after_order_date', 'Day(s) after the confirmation date'),
            ('fix_day_following_order_month', 'Day(s) after the end of the order month (Net EOM)'),
        ],
        default='day_after_invoice_date', required=True, string='Options'
        )
