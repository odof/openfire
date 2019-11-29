# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare
from odoo.exceptions import UserError
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

class OfDocumentsJoints(models.AbstractModel):
    """ Classe abstraite qui permet d'ajouter les documents joints.
    Elle doit être surchargée pour ajouter d'autres rapports dans la fonction _allowed_reports
    et être en héritage pour la classe sur laquelle on veut ajouter la fonctionnalité.
    """
    _name = 'of.documents.joints'

    of_mail_template_ids = fields.Many2many("of.mail.template", string="Documents joints", help=u"Intégrer des documents pdf au devis/bon de commande (exemple : CGV)")

    @api.model
    def _allowed_reports(self):
        """
        Fonction qui affecte un nom de rapport à un modèle.
        Si le nom de rapport imprimé n'est pas dans la liste de clés du dictionnaire,
        alors les documents joints ne seront pas imprimés.
        :return: {'nom_du_rapport' : modèle.concerné'}
        """
        return {'sale.report_saleorder': 'sale.order', 'account.report_invoice': 'account.invoice'}

    @api.multi
    def _detect_doc_joint(self):
        """
        Cette fonction retourne les données des documents à joindre au fichier pdf du devis/commande au format binaire.
        Le document retourné correspond au fichier pdf joint au modéle de courrier.
        @todo: Permettre l'utilisation de courriers classiques et le remplissage des champs.
        :return: liste des documents à ajouter à la suite du rapport
        """
        self.ensure_one()
        compose_mail_obj = self.env['of.compose.mail']
        attachment_obj = self.env['ir.attachment']
        data = []
        for mail_template in self.of_mail_template_ids:
            if mail_template.file:
                # Utilisation des documents pdf fournis
                if not mail_template.chp_ids:
                    data.append(mail_template.file)
                    continue
                # Calcul des champs remplis sur le modèle de courrier
                attachment = attachment_obj.search([('res_model', '=', mail_template._name),
                                                    ('res_field', '=', 'file'),
                                                    ('res_id', '=', mail_template.id)])
                datas = dict(compose_mail_obj.eval_champs(self, mail_template.chp_ids))
                file_path = attachment_obj._full_path(attachment.store_fname)
                fd, generated_pdf = tempfile.mkstemp(prefix='doc_joint_', suffix='.pdf')
                try:
                    pypdftk.fill_form(file_path, datas, out_file=generated_pdf, flatten=not mail_template.fillable)
                    with open(generated_pdf, "rb") as encode:
                        encoded_file = base64.b64encode(encode.read())
                finally:
                    os.close(fd)
                    try:
                        os.remove(generated_pdf)
                    except Exception:
                        pass
                data.append(encoded_file)
        return data


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'of.documents.joints']

    def pdf_afficher_multi_echeances(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_afficher_multi_echeances')

    def pdf_afficher_nom_parent(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_nom_parent')

    def pdf_afficher_civilite(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_civilite')

    def pdf_afficher_telephone(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_telephone') or 0

    def pdf_afficher_mobile(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_mobile') or 0

    def pdf_afficher_fax(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_fax') or 0

    def pdf_afficher_email(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_email') or 0

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

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Compute the total amounts of the SO."""
        # Le calcul standard diffère du calcul utilisé dans les factures, ce qui peut mener à des écarts dans certains cas
        # (quand l'option d'arrondi global de la tva est utilisée et que la commande contient plusieurs lignes avec des taxes différentes).
        # On uniformise le calcul du montant des devis/commandes avec celui des factures.
        for order in self:
            order.amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            order.amount_tax = sum(tax['amount'] for tax in order.of_get_taxes_values().itervalues())
            order.amount_total = order.amount_untaxed + order.amount_tax

    of_to_invoice = fields.Boolean(u"Entièrement facturable", compute='_compute_of_to_invoice', search='_search_of_to_invoice')
    of_notes_facture = fields.Html(string="Notes facture", oldname="of_notes_factures")
    of_notes_intervention = fields.Html(string="Notes intervention")
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)

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
    def of_get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.order_line:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(price_unit, self.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=self.partner_shipping_id)['taxes']
            for val in taxes:
                key = val['account_id']

                if key not in tax_grouped:
                    tax_grouped[key] = {
                        'tax_id': val['id'],
                        'amount': val['amount'],
                        'base': round_curr(val['base'])
                    }
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])

        for values in tax_grouped.itervalues():
            values['base'] = round_curr(values['base'])
            values['amount'] = round_curr(values['amount'])
        return tax_grouped

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

    def toggle_view(self):
        """ Permet de basculer entre la vue vendeur/client
        """
        self.of_client_view = not self.of_client_view

    @api.multi
    def _of_get_total_lines_by_group(self):
        """
        Retourne les lignes de la commande, séparées en fonction du groupe dans lequel les afficher.
        Les groupes sont ceux définis par l'objet of.invoice.report.total, permettant de déplacer le rendu des
          lignes de commande sous le total hors taxe ou TTC.
        Les groupes sont affichés dans leur ordre propre, puis les lignes dans l'ordre de leur apparition dans la commande.
        @param return: Liste de couples (groupe, lignes de commande). Le premier élément vaut (False, Lignes non groupées).
        """
        self.ensure_one()
        group_obj = self.env['of.invoice.report.total.group']

        lines = self.order_line
        products = lines.mapped('product_id')
        product_ids = list(products._ids)
        categ_ids = list(products.mapped('categ_id')._ids)
        groups = group_obj.search([('order', '=', True),
                                   '|', ('id', '=', group_obj.get_group_paiements().id),
                                   '|', ('product_ids', 'in', product_ids), ('categ_ids', 'in', categ_ids)])

        result = []
        for group in groups:
            if group.is_group_paiements():
                group_paiement_lines = group.filter_lines(lines)
                if group_paiement_lines is not False:
                    lines -= group_paiement_lines
                break
        for group in groups:
            if group.is_group_paiements():
                result.append((group, group_paiement_lines))
            else:
                group_lines = group.filter_lines(lines)
                if group_lines is not False:
                    # On ajoute cette vérification pour ne pas afficher des lignes à 0 dans les paiements et
                    # ne pas afficher le groupe si toutes les lignes sont à 0.
                    group_lines_2 = group_lines.filtered(lambda l: l.price_subtotal)
                    if group_lines_2:
                        result.append((group, group_lines_2))
                    lines -= group_lines  # On enlève quand même toutes les lignes du groupe pour ne pas qu'elle s'affichent
        if lines:
            result = [(False, lines)] + result
        else:
            result = [(False, self.order_line.mapped('invoice_lines'))]
            # On ajoute quand-même les paiements
            for group in groups:
                if group.is_group_paiements():
                    result.append((group, lines))  # lines est vide
        return result

    @api.multi
    def _of_get_printable_lines(self):
        """ [IMPRESSION]
        Renvoie les lignes à afficher
        """
        return self._of_get_total_lines_by_group()[0][1]

    def _prepare_tax_line_vals(self, line, tax):
        """ Emulation de la fonction du même nom du modèle 'account.invoice'
            Permet de récupérer la clé de groupement dans _of_get_printable_totals
        """
        vals = {
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] or False,
            'account_id': tax['account_id'] or tax['refund_account_id'] or False,

        }
        return vals

    @api.multi
    def _of_get_printable_totals(self):
        """ [IMPRESSION]
        Retourne un dictionnaire contenant les valeurs à afficher dans les totaux de la commande pdf.
        Dictionnaire de la forme :
        {
            'subtotal' : Total HT des lignes affichées,
            'untaxed' : [[('libellé', montant),...], ('libellé total': montant_total)]
            'taxes' : idem,
            'total' : idem,
        }
        Les listes untaxed, taxes et total pourraient être regroupés en une seule.
        Ce format pourra aider aux héritages (?).
        """
        self.ensure_one()
        tax_obj = self.env['account.tax']
        round_curr = self.currency_id.round

        group_lines = self._of_get_total_lines_by_group()

        result = {}
        result['subtotal'] = sum(group_lines[0][1].mapped('price_subtotal'))
        total_amount = result['subtotal']

        i = 1
        untaxed_lines = group_lines[0][1]
        # --- Sous-totaux hors taxes ---
        result_untaxed = []
        while i < len(group_lines) and group_lines[i][0].position == '0-ht':
            group, lines = group_lines[i]
            i += 1
            untaxed_lines |= lines
            lines_vals = []
            for line in lines:
                lines_vals.append((line.of_get_line_name()[0], line.price_subtotal))
                total_amount += line.price_subtotal
            total_vals = (group.subtotal_name, round_curr(total_amount))
            result_untaxed.append([lines_vals, total_vals])
        result['untaxed'] = result_untaxed

        # --- Ajout des taxes ---
        # Code copié depuis account.invoice.get_taxes_values()
        tax_grouped = {}
        for line in untaxed_lines:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price_unit, self.currency_id, line.product_uom_qty, line.product_id, self.partner_id)['taxes']
            for tax_val in taxes:
                val = self._prepare_tax_line_vals(line, tax_val)
                tax = tax_obj.browse(tax_val['id'])
                key = tax.get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['name'] = tax.description or tax.name
                    tax_grouped[key]['group'] = tax.tax_group_id
                else:
                    tax_grouped[key]['amount'] += val['amount']
        # Taxes groupées par groupe de taxes (cf account.invoice._get_tax_amount_by_group())
        tax_vals_dict = {}
        for tax in sorted(tax_grouped.values(), key=lambda t: t['name']):
            amount = round_curr(tax['amount'])
            tax_vals_dict.setdefault(tax['group'], [tax['group'].name, 0])
            tax_vals_dict[tax['group']][1] += amount
            total_amount += amount
        result['taxes'] = [[tax_vals_dict.values(), (_("Total"), round_curr(total_amount))]]

        # --- Sous-totaux TTC ---
        result_total = []
        while i < len(group_lines):
            # Tri des paiements par date
            group, lines = group_lines[i]
            i += 1
            if group.is_group_paiements():
                lines_vals = self._of_get_printable_payments(lines)
                if not lines_vals:
                    continue
                for line in lines_vals:
                    total_amount -= line[1]
            else:
                lines_vals = []
                for line in lines:
                    lines_vals.append((line.of_get_line_name()[0], line.price_total))
                    total_amount += line.price_total
            total_vals = (group.subtotal_name, round_curr(total_amount))
            result_total.append([lines_vals, total_vals])
        result['total'] = result_total

        return result

    @api.multi
    def order_lines_layouted(self):
        """
        Retire les lignes de commande qui doivent êtres affichées dans les totaux.
        """
        report_pages_full = super(SaleOrder, self).order_lines_layouted()
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

    @api.multi
    def _of_get_printable_payments(self, order_lines):
        """ [IMPRESSION]
        Renvoie les lignes à afficher.
        Permet l'affichage des paiements dans une commande.
        On ne va pas chercher les paiements affectés à la commande car le lien est ajouté dans of_sale_payment
        """
        invoice_obj = self.env['account.invoice']
        account_move_line_obj = self.env['account.move.line']
        # Liste des factures et factures d'acompte
        invoices = self.mapped('order_line').mapped('invoice_lines').mapped('invoice_id')

        # Retour de tous les paiements des factures
        # On distingue les paiements de la facture principale de ceux des factures liées
        result = []
        for invoice in invoices:
            widget = json.loads(invoice.payments_widget.replace("'", "\'"))
            if not widget:
                continue
            for payment in widget.get('content', []):
                # Les paiements sont classés dans l'ordre chronologique
                move_line = account_move_line_obj.browse(payment['payment_id'])
                name = invoice_obj._of_get_payment_display(move_line)
                result.append((name, payment['amount']))
        return result

    @api.multi
    def _prepare_invoice(self):
        """ Rajout date visite technique. Attention en cas de facturation de plusieurs bons de commande à la fois"""
        self.ensure_one()
        if self.company_id:
            self = self.with_context(company_id=self.company_id.id)
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals["of_date_vt"] = self.of_date_vt
        return invoice_vals


class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        allowed_reports = self.env['of.documents.joints']._allowed_reports()
        if report_name in allowed_reports:
            # On ajoute au besoin les documents joint
            model = self.env[allowed_reports[report_name]].browse(docids)[0]
            mails_data = model._detect_doc_joint()
            if mails_data:
                fd, order_pdf = tempfile.mkstemp()
                os.write(fd, result)
                os.close(fd)
                file_paths = [order_pdf]

                for mail_data in mails_data:
                    fd, mail_pdf = tempfile.mkstemp()
                    os.write(fd, base64.b64decode(mail_data))
                    os.close(fd)
                    file_paths.append(mail_pdf)

                result_file_path = self.env['report']._merge_pdf(file_paths)
                try:
                    result_file = file(result_file_path, "rb")
                    result = result_file.read()
                    result_file.close()
                    for file_path in file_paths:
                        os.remove(file_path)
                    os.remove(result_file_path)
                except Exception:
                    pass
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
        if lines._name == 'account.invoice.line':
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
        else:
            return lines.filtered(lambda l: l.product_id in self.product_ids or
                                            l.product_id.categ_id in self.categ_ids)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_unit = fields.Float(digits=False)
    of_client_view = fields.Boolean(string="Vue client/vendeur", related="order_id.of_client_view")
    of_article_principal = fields.Boolean(string="Article principal", help="Cet article est l'article principal de la commande")
    of_product_categ_id = fields.Many2one(
        'product.category', related='product_id.categ_id', string=u"Catégorie d'article",
        store=True, index=True
    )
    date_order = fields.Datetime(related='order_id.date_order', string="Date de commande", store=True, index=True)

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

    def _write(self, vals):
        for field in vals:
            if field != 'of_product_categ_id':
                break
        else:
            self = self.sudo()
        return super(SaleOrderLine, self)._write(vals)

    @api.multi
    def unlink(self):
        """
        Ne pas autoriser la suppression de ligne de commandes si la ligne est déjà présente sur une facture qui n'est
        pas une facture annulée n'ayant jamais été validée.
        """
        locked_invoice_lines = self.mapped('invoice_lines').filtered(lambda l: l.invoice_id.state != 'cancel' or l.invoice_id.move_name)
        if locked_invoice_lines:
            raise UserError(u"""Vous ne pouvez supprimer une ligne d'article liée à une facture.\n"""
                            u"""Veuillez annuler vos modifications.""")
        return super(SaleOrderLine, self).unlink()

    @api.multi
    def write(self, vals):
        """
        Si un des champ de blocked est présent ET une ligne modifiée ne doit pas avoir de modification alors renvoi une
        erreur. Le champ of_discount_formula est dans le module of_sale_discount, la façon dont on vérifie la présence
        des champs dans vals ne provoque pas d'erreur si le module n'est pas installé.
        TODO: Permettre de modifier le montant si modification viens de la facture d'acompte
        """
        blocked = [x for x in ('price_unit', 'product_uom_qty', 'product_uom', 'discount', 'of_discount_formula') if x in vals.keys()]
        for line in self:
            locked_invoice_lines = line.mapped('invoice_lines').filtered(lambda l: l.of_is_locked)
            if locked_invoice_lines and blocked:
                raise UserError(u"""Cette ligne ne peut être modifiée : %s""" % line.name)
        return super(SaleOrderLine, self).write(vals)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    price_unit = fields.Float(digits=False)
    of_is_locked = fields.Boolean(compute="_compute_is_locked", string=u"Article particulié")

    @api.model
    def get_locked_categories(self):
        """
        Fait dans une fonction pour faciliter l'héritage.
        :return: Renvoie une liste de catégories dont les articles ne dont le montant ne doit pas changer des bons de commandes
        """
        return [self.env['ir.values'].get_default('sale.config.settings',
                                                  'of_deposit_product_categ_id_setting')]

    @api.model
    def get_locked_products(self):
        """
        Fait dans une fonction pour faciliter l'héritage.
        :return: Renvoie une liste d'articles qui ne doivent pas être supprimés des bons de commandes
        """
        return []

    @api.depends('product_id')
    def _compute_is_locked(self):
        """
        of_is_locked est un champ qui permet de savoir si une ligne de facture doit empêcher sa contrepartie sur bon
        de commande d'être supprimée (voir sale.order.line.unlink())
        """
        locked_categories = self.get_locked_categories()
        locked_products = self.get_locked_products()
        for invoice_line in self:
            if invoice_line.product_id.categ_id.id not in locked_categories and \
               invoice_line.product_id.id not in locked_products:
                invoice_line.of_is_locked = False
            else:
                invoice_line.of_is_locked = True

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
        help=u"La description du fabricant d'un article sera ajoutée à la description de l'article dans les documents."
    )


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def _auto_init(self):
        """
        Certain paramètres d'affichage sont passés de Booléen à Sélection.
        Cette fonction est appelée à chaque mise à jour mais ne fait quelque chose que la première fois qu'elle est appelée.
        """
        set_value = False
        if not self.env['ir.values'].get_default('sale.config.settings', 'bool_vers_selection_fait'):  # Cette fonction n'a encore jamais été appelée
            set_value = True
        super(OFSaleConfiguration, self)._auto_init()
        if set_value:
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_telephone'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_telephone', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_telephone', 0)
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_mobile'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_mobile', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_mobile', 0)
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_fax'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_fax', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_fax', 0)
            if self.env['ir.values'].get_default('sale.config.settings', 'pdf_adresse_email'):
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_email', 1)
            else:
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'pdf_adresse_email', 0)
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'bool_vers_selection_fait', True)

    of_deposit_product_categ_id_setting = fields.Many2one(
        'product.category',
        string=u"(OF) Catégorie des acomptes",
        help=u"Catégorie des articles utilisés pour les acomptes")

    stock_warning_setting = fields.Boolean(
        string="(OF) Stock", required=True, default=False,
        help="Afficher les messages d'avertissement de stock ?")

    pdf_display_product_ref_setting = fields.Boolean(
        string=u"(OF) Réf. produits", required=True, default=False,
        help=u"Afficher les références produits dans les rapports PDF ?")

    pdf_date_validite_devis = fields.Boolean(
        string=u"(OF) Date validité devis", required=True, default=False,
        help=u"Afficher la date de validité dans le rapport PDF des devis ?")

    pdf_adresse_nom_parent = fields.Boolean(
        string=u"(OF) Nom parent contact", required=True, default=False,
        help=u"Afficher le nom du 'parent' du contact au lieu du nom du contact dans les rapport PDF ?")
    pdf_adresse_civilite = fields.Boolean(
        string=u"(OF) Civilités", required=True, default=False,
        help=u"Afficher la civilité dans les rapport PDF ?")
    pdf_adresse_telephone = fields.Selection([
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Téléphone",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_mobile = fields.Selection([
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Mobile",
        help=u"Où afficher le numéro de téléphone mobile dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_fax = fields.Selection([
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) Fax",
        help=u"Où afficher le fax dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_email = fields.Selection([
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) E-mail",
        help=u"Où afficher l'adresse email dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_afficher_multi_echeances = fields.Boolean(
        string=u"(OF) Multi-échéances", required=True, default=False,
        help=u"Afficher les échéances multiples dans les rapports PDF ?")
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
    _name = 'account.invoice'
    _inherit = ["account.invoice", "of.documents.joints"]

    of_date_vt = fields.Date(string="Date visite technique")
    of_sale_order_ids = fields.Many2many('sale.order', compute="_compute_of_sale_order_ids", string="Bons de commande")
    of_residual = fields.Float(string=u"Somme du montant non payé des factures d'acompte et de la facture finale", compute="_compute_of_residual")
    of_residual_equal = fields.Boolean(compute="_compute_of_residual")
    of_suivi_interne = fields.Char(string="Suivi interne")

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
        self.ensure_one()
        invoices = self
        to_check = lines.mapped('sale_line_ids').mapped('invoice_lines').mapped('invoice_id')
        while to_check:
            invoices |= to_check
            to_check = (to_check
                        .mapped('invoice_line_ids')
                        .mapped('sale_line_ids')
                        .mapped('invoice_lines')
                        .mapped('invoice_id')) - invoices
        return invoices.filtered(lambda i: i.type == self.type)

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
    last = fields.Boolean(string=u"Dernière Échéance", compute="_compute_last")

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


class SaleLayoutCategory(models.Model):
    _inherit = 'sale.layout_category'

    active = fields.Boolean(string="Active", default=True)
