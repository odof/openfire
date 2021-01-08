# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.addons.sale.models.sale import SaleOrderLine as SOL
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError
from odoo.models import regex_order
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


@api.onchange('product_uom', 'product_uom_qty')
def product_uom_change(self):
    u"""Copie de la fonction parente avec retrait de l'affectation du prix unitaire"""
    if not self.product_uom or not self.product_id:
        self.price_unit = 0.0
        return
    if self.order_id.pricelist_id.of_is_quantity_dependent(self.product_id.id, self.order_id.date_order) \
            and self.order_id.partner_id \
            and (not self.price_unit or float_compare(self.price_unit, self.product_id.list_price, 2) != 0):
        self.price_unit = self.of_get_price_unit()

SOL.product_uom_change = product_uom_change


class OfDocumentsJoints(models.AbstractModel):
    """ Classe abstraite qui permet d'ajouter les documents joints.
    Elle doit être surchargée pour ajouter d'autres rapports dans la fonction _allowed_reports
    et être en héritage pour la classe sur laquelle on veut ajouter la fonctionnalité.
    """
    _name = 'of.documents.joints'

    of_mail_template_ids = fields.Many2many(
        "of.mail.template", string="Documents joints",
        help=u"Intégrer des documents pdf au devis/bon de commande (exemple : CGV)"
    )

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

    def pdf_vt_pastille(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'pdf_vt_pastille')

    def get_color_section(self):
        return self.env['ir.values'].get_default('sale.config.settings', 'of_color_bg_section')

    def _search_of_to_invoice(self, operator, value):
        # Récupération des bons de commande non entièrement livrés
        self._cr.execute("SELECT DISTINCT order_id\n"
                         "FROM sale_order_line\n"
                         "WHERE qty_to_invoice + qty_invoiced < product_uom_qty")
        order_ids = self._cr.fetchall()

        domain = ['&', '&',
                  ('of_force_invoice_status', 'not in', ('invoiced', 'no')),
                  ('state', 'in', ('sale', 'done')),
                  ('order_line.qty_to_invoice', '>', 0)]
        if order_ids:
            domain = ['&'] + domain + [('id', 'not in', zip(*order_ids)[0])]
        return domain

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Compute the total amounts of the SO."""
        # Le calcul standard diffère du calcul utilisé dans les factures, cela peut mener à des écarts dans certains cas
        # (quand l'option d'arrondi global de la tva est utilisée
        # et que la commande contient plusieurs lignes avec des taxes différentes).
        # On uniformise le calcul du montant des devis/commandes avec celui des factures.
        for order in self:
            order.amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            order.amount_tax = sum(tax['amount'] for tax in order.of_get_taxes_values().itervalues())
            order.amount_total = order.amount_untaxed + order.amount_tax

    of_to_invoice = fields.Boolean(
        u"Entièrement facturable", compute='_compute_of_to_invoice', search='_search_of_to_invoice'
    )
    of_notes_facture = fields.Html(string="Notes facture", oldname="of_notes_factures")
    of_notes_intervention = fields.Html(string="Notes intervention")
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)

    of_total_cout = fields.Monetary(compute='_compute_of_marge', string='Prix de revient')
    of_marge_pc = fields.Float(compute='_compute_of_marge', string='Marge %')

    of_etiquette_partenaire_ids = fields.Many2many(
        'res.partner.category', related='partner_id.category_id', string=u"Étiquettes client")
    of_client_view = fields.Boolean(string='Vue client/vendeur')

    of_date_vt = fields.Date(
        string="Date visite technique", help=u"Si renseignée apparaîtra sur le devis / Bon de commande"
    )
    of_echeance_line_ids = fields.One2many('of.sale.echeance', 'order_id', string=u"Échéances")

    of_echeances_modified = fields.Boolean(
        u"Les échéances ont besoin d'être recalculées", compute="_compute_of_echeances_modified")
    of_force_invoice_status = fields.Selection([
        ('invoiced', 'Fully Invoiced'),
        ('no', 'Nothing to Invoice')
        ], string=u"Forcer état de facturation",
        help=u"Permet de forcer l'état de facturation de la commande.\n"
             u"Utile pour les commandes facturées qui refusent de changer d'état "
             u"(e.g. une ligne a été supprimée dans la facture).", copy=False
    )
    of_invoice_policy = fields.Selection(
        [('order', u'Quantités commandées'), ('delivery', u'Quantités livrées')], string="Politique de facturation"
    )
    of_fixed_invoice_date = fields.Date(string="Date de facturation fixe")
    of_invoice_date_prev = fields.Date(string=u"Date de facturation prévisonnelle",
                                       compute="_compute_of_invoice_date_prev",
                                       inverse="_inverse_of_invoice_date_prev", store=True)
    of_delivered = fields.Boolean(string=u"Livrée", compute="_compute_delivered", store=True)

    @api.depends('of_echeance_line_ids', 'amount_total')
    def _compute_of_echeances_modified(self):
        for order in self:
            order.of_echeances_modified = bool(order.of_echeance_line_ids
                                               and float_compare(order.amount_total,
                                                                 sum(order.of_echeance_line_ids.mapped('amount')),
                                                                 precision_rounding=.01))

    @api.depends('order_line', 'order_line.qty_delivered', 'order_line.product_uom_qty')
    def _compute_delivered(self):
        for order in self:
            for line in order.order_line:
                if float_compare(line.qty_delivered, line.product_uom_qty, 2) < 0:
                    order.of_delivered = False
                    break
            else:
                order.of_delivered = True

    @api.depends('of_fixed_invoice_date', 'of_invoice_policy',
                 'order_line', 'order_line.of_invoice_date_prev',
                 'order_line.procurement_ids', 'order_line.procurement_ids.move_ids',
                 'order_line.procurement_ids.move_ids.picking_id.min_date')
    def _compute_of_invoice_date_prev(self):
        for order in self:
            if order.of_fixed_invoice_date or order.of_invoice_policy == 'order':
                order.of_invoice_date_prev = order.of_fixed_invoice_date
            elif order.of_invoice_policy == 'delivery':
                pickings = order.order_line.mapped('procurement_ids')\
                                           .mapped('move_ids')\
                                           .mapped('picking_id')\
                                           .sorted('min_date')
                if pickings:
                    order.of_invoice_date_prev = fields.Date.to_string(fields.Date.from_string(pickings[0].min_date))

    def _inverse_of_invoice_date_prev(self):
        for order in self:
            order.of_fixed_invoice_date = order.of_invoice_date_prev

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

    @api.depends('state', 'order_line.invoice_status', 'of_force_invoice_status')
    def _get_invoiced(self):
        # Appel du super dans tous les cas pour le calcul de invoice_count et invoice_ids
        super(SaleOrder, self)._get_invoiced()
        for order in self:
            if order.of_force_invoice_status:
                order.invoice_status = order.of_force_invoice_status

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        self.of_invoice_policy = self.partner_id and self.partner_id.of_invoice_policy or False

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
            if order.state not in ('sale', 'done') or order.of_force_invoice_status in ('invoiced', 'no'):
                order.of_to_invoice = False
                continue
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
        Les groupes sont affichés dans leur ordre propre, puis les lignes dans l'ordre d'apparition dans la commande.
        @param return: Liste de couples (groupe, lignes de commande). Le 1er élément vaut (False, Lignes non groupées).
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
                    # On enlève quand même toutes les lignes du groupe pour ne pas qu'elle s'affichent
                    lines -= group_lines
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
            taxes = line.tax_id.compute_all(price_unit, self.currency_id, line.product_uom_qty, line.product_id,
                                            self.partner_id)['taxes']
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
        result['taxes'] = [[tax_vals_dict.values(), (_("Total TTC"), round_curr(total_amount))]]

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

    @api.multi
    def copy(self, default=None):
        res = super(SaleOrder, self).copy(default=default)
        res._onchange_payment_term_id()
        return res


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
    def filter_lines(self, lines, invoices=None):
        self.ensure_one()
        if not self.is_group_paiements():
            return super(OFInvoiceReportTotalGroup, self).filter_lines(lines, invoices=invoices)
        # Retour des lignes dont l'article correspond à un groupe de rapport de facture
        #   et dont la ligne de commande associée a une date antérieure
        #   (seul un paiement d'une facture antérieure doit figurer sur une facture)
        if lines._name == 'account.invoice.line':
            allowed_order_lines = invoices.mapped('invoice_line_ids').mapped('sale_line_ids')
            lines = lines.filtered(lambda l: ((l.product_id in self.product_ids
                                               or l.product_id.categ_id in self.categ_ids)
                                              and l.sale_line_ids
                                              and l.sale_line_ids in allowed_order_lines))
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
            return lines.filtered(lambda l: (l.product_id in self.product_ids or
                                             l.product_id.categ_id in self.categ_ids))


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'of.readgroup']

    price_unit = fields.Float(digits=False, help="""
    Prix unitaire de l'article.
    À entrer HT ou TTC suivant la TVA de la ligne de commande.
    """)
    of_client_view = fields.Boolean(string="Vue client/vendeur", related="order_id.of_client_view")
    of_article_principal = fields.Boolean(
        string="Article principal", help="Cet article est l'article principal de la commande"
    )
    of_product_categ_id = fields.Many2one(
        'product.category', related='product_id.categ_id', string=u"Catégorie d'article", store=True, index=True)
    date_order = fields.Datetime(related='order_id.date_order', string="Date de commande", store=True, index=True)
    confirmation_date_order = fields.Datetime(
        related='order_id.confirmation_date', string="Date de confirmation de commande", store=True, index=True)
    of_gb_partner_tag_id = fields.Many2one(
        'res.partner.category', compute=lambda *a, **k: {}, search='_search_of_gb_partner_tag_id',
        string="Étiquette client", of_custom_groupby=True
    )
    of_price_unit_display = fields.Float(related='product_id.list_price', string=u"Prix unitaire", readonly=True)
    of_product_forbidden_discount = fields.Boolean(
        related='product_id.of_forbidden_discount', string=u"Remise interdite pour ce produit", readonly=True)

    of_price_unit_ht = fields.Float(
        string='Unit Price excl', compute='_compute_of_price_unit', help="Unit price without taxes", store=True
    )
    of_price_unit_ttc = fields.Float(
        string='Unit Price incl', compute='_compute_of_price_unit', help="Unit price with taxes", store=True
    )
    of_product_default_code = fields.Char(related='product_id.default_code', string=u"Référence article", readonly=True)
    of_order_line_option_id = fields.Many2one(comodel_name='of.order.line.option', string=u"Option")
    of_reset_option = fields.Boolean(string=u"Réinitialiser l'option ?")

    of_confirmation_date = fields.Datetime(string="Date de confirmation", related="order_id.confirmation_date", store=True)
    of_invoice_policy = fields.Selection([('order', u'Quantités commandées'), ('delivery', u'Quantités livrées')],
                                         string="Politique de facturation",
                                         compute="_compute_of_invoice_policy",
                                         store=True)
    of_invoice_date_prev = fields.Date(string=u"Date de facturation prévisionnelle",
                                       compute="_compute_of_invoice_date_prev",
                                       store=True)

    @api.depends('price_unit', 'order_id.currency_id', 'order_id.partner_shipping_id', 'product_id',
                 'price_subtotal', 'product_uom_qty')
    def _compute_of_price_unit(self):
        """
        @ TODO: à fusionner avec _compute_amount
        :return:
        """
        for line in self:
            taxes = line.tax_id.compute_all(line.price_unit, line.order_id.currency_id, 1,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.of_price_unit_ht = taxes['total_excluded']
            line.of_price_unit_ttc = taxes['total_included']

    @api.depends('product_id', 'product_id.invoice_policy',
                 'order_id', 'order_id.of_invoice_policy',
                 'order_partner_id', 'order_partner_id.of_invoice_policy')
    def _compute_of_invoice_policy(self):
        for line in self:
            line.of_invoice_policy = line.order_id.of_invoice_policy \
                                     or line.order_partner_id.of_invoice_policy or line.product_id.invoice_policy \
                                     or self.env['ir.values'].get_default('product_template', 'invoice_policy')

    @api.depends('of_invoice_policy',
                 'order_id', 'order_id.of_fixed_invoice_date',
                 'procurement_ids', 'procurement_ids.move_ids', 'procurement_ids.move_ids')
    def _compute_of_invoice_date_prev(self):
        for line in self:
            if line.of_invoice_policy == 'order':
                line.of_invoice_date_prev = line.order_id.of_invoice_date_prev
            elif line.of_invoice_policy == 'delivery':
                moves = line.procurement_ids.mapped('move_ids').sorted('date_expected')
                if moves:
                    line.of_invoice_date_prev = fields.Date.to_string(fields.Date.from_string(moves[0].date_expected))

    @api.model
    def _search_of_gb_partner_tag_id(self, operator, value):
        return [('order_partner_id.category_id', operator, value)]

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'of_gb_partner_tag_id':
            return super(SaleOrderLine, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'res_partner_res_partner_category_rel', 'order_partner_id', 'partner_id', 'partner_category'),
            implicit=False, outer=True,
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".category_id' % (alias,)
        }

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, reverse_direction, seen):
        if order_field == 'of_gb_partner_tag_id':
            dest_model = self.env['res.partner.category']
            m2o_order = dest_model._order
            if not regex_order.match(m2o_order):
                # _order is complex, can't use it here, so we default to _rec_name
                m2o_order = dest_model._rec_name

            rel_alias, _ = query.add_join(
                (alias, 'res_partner_res_partner_category_rel', 'order_partner_id', 'partner_id', 'partner_category_rel'),
                implicit=False, outer=True)
            dest_alias, _ = query.add_join(
                (rel_alias, 'res_partner_category', 'category_id', 'id', 'partner_category'),
                implicit=False, outer=True)
            return dest_model._generate_order_by_inner(dest_alias, m2o_order, query,
                                                       reverse_direction, seen)
        return []

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

        # Remise interdite
        if self.product_id and self.product_id.of_forbidden_discount and self.of_discount_formula:
            self.of_discount_formula = False
        if self.product_id and self.product_id.categ_id:
            self.of_article_principal = self.product_id.categ_id.of_article_principal
        if self.env.user.has_group('sale.group_sale_layout'):
            if self.product_id and self.product_id.categ_id.of_layout_id:
                self.layout_category_id = self.product_id.categ_id.of_layout_id

        return res

    @api.onchange('of_order_line_option_id')
    def _onchange_of_order_line_option_id(self):
        if self.of_order_line_option_id and self.product_id:
            option = self.of_order_line_option_id
            if option.sale_price_update and self.price_unit:
                if option.sale_price_update_type == 'fixed':
                    self.price_unit = self.price_unit + option.sale_price_update_value
                elif option.sale_price_update_type == 'percent':
                    self.price_unit = self.price_unit + self.price_unit * (option.sale_price_update_value / 100)
                self.price_unit = self.order_id.currency_id.round(self.price_unit)
            if option.purchase_price_update and self.purchase_price:
                if option.purchase_price_update_type == 'fixed':
                    self.purchase_price = (self.product_id.of_seller_price + option.purchase_price_update_value) *\
                                          self.product_id.property_of_purchase_coeff
                elif option.purchase_price_update_type == 'percent':
                    self.purchase_price = (self.product_id.of_seller_price +
                                           (self.product_id.of_seller_price *
                                            (option.purchase_price_update_value / 100))) *\
                                          self.product_id.property_of_purchase_coeff
                self.purchase_price = self.order_id.currency_id.round(self.purchase_price)
            if option.description_update:
                self.name = self.name + "\n%s" % option.description_update

    @api.onchange('of_reset_option')
    def _onchange_of_reset_option(self):
        if self.of_reset_option:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id
            )

            if self.order_id.pricelist_id and self.order_id.partner_id:
                self.price_unit = self.env['account.tax']._fix_tax_included_price_company(
                    self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
            self.purchase_price = product.standard_price
            if self.of_order_line_option_id.description_update:
                self.name = self.name.replace(self.of_order_line_option_id.description_update, '')
            self.of_order_line_option_id = False
            self.of_reset_option = False

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
        locked_invoice_lines = self.mapped('invoice_lines').filtered(
            lambda l: l.invoice_id.state != 'cancel' or l.invoice_id.move_name)
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
        force = self._context.get('force_price')
        blocked = [x for x in ('price_unit', 'product_uom_qty', 'product_uom', 'discount', 'of_discount_formula')
                   if x in vals.keys()]
        for line in self:
            locked_invoice_lines = line.mapped('invoice_lines').filtered(lambda l: l.of_is_locked)
            if locked_invoice_lines and blocked and not force:
                raise UserError(u"""Cette ligne ne peut être modifiée : %s""" % line.name)
        return super(SaleOrderLine, self).write(vals)

    @api.multi
    def _additionnal_tax_verifications(self):
        invoice_line_obj = self.env['account.invoice.line']
        if self.product_id and self.product_id.id in invoice_line_obj.get_locked_product_ids():
            return True
        if self.product_id and self.product_id.categ_id and self.product_id.categ_id.id in invoice_line_obj.\
                get_locked_category_ids():
            return True
        return False

    @api.multi
    def _compute_tax_id(self):
        return super(SaleOrderLine, self.filtered(lambda line: not line._additionnal_tax_verifications())).\
            _compute_tax_id()

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_get_to_invoice_qty()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs only in state 'sale', so that when a SO is set to done, the upselling opportunity
          is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            invoice_policy = line.of_invoice_policy
            if line.state not in ('sale', 'done'):
                line.invoice_status = 'no'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state == 'sale' and invoice_policy == 'order' and \
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            invoice_policy = line.order_id.of_invoice_policy
            if not invoice_policy:
                invoice_policy = line.product_id.invoice_policy
            if line.order_id.state in ['sale', 'done']:
                if invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    def of_get_price_unit(self):
        """Renvoi le prix unitaire type."""
        self.ensure_one()
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )
        return self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product),
                                                                       product.taxes_id, self.tax_id,
                                                                       self.company_id)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    price_unit = fields.Float(digits=False)
    of_is_locked = fields.Boolean(compute="_compute_is_locked", string=u"Article particulier")

    @api.model
    def get_locked_category_ids(self):
        """
        Fait dans une fonction pour faciliter l'héritage.
        :return: Ids des catégories dont le montant des articles ne doit pas changer des bons de commandes
        """
        return [self.env['ir.values'].get_default('sale.config.settings',
                                                  'of_deposit_product_categ_id_setting')]

    @api.model
    def get_locked_product_ids(self):
        """
        Fait dans une fonction pour faciliter l'héritage.
        :return: Ids des articles qui ne doivent pas être supprimés des bons de commandes
        """
        return []

    @api.depends('product_id')
    def _compute_is_locked(self):
        """
        of_is_locked est un champ qui permet de savoir si une ligne de facture doit empêcher sa contrepartie sur bon
        de commande d'être supprimée (voir sale.order.line.unlink())
        """
        locked_category_ids = self.get_locked_category_ids()
        locked_product_ids = self.get_locked_product_ids()
        for invoice_line in self:
            if invoice_line.product_id.categ_id.id not in locked_category_ids and \
               invoice_line.product_id.id not in locked_product_ids:
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

    @api.multi
    def write(self, vals):
        fields_to_sync = {
            'price_unit': 'price_unit',
            'uom_id': 'product_uom',
            'discount': 'discount',
            'of_discount_formula': 'of_discount_formula',
            'invoice_line_tax_ids': 'tax_id'
        }
        res = super(AccountInvoiceLine, self).write(vals)
        if res:
            for line in self.filtered('of_is_locked'):
                if line.invoice_id.invoice_line_ids.filtered('of_is_locked') == line.invoice_id.invoice_line_ids \
                   and len(line.sale_line_ids) == 1 and line.sale_line_ids.invoice_lines == line:
                    sync = [x for x in fields_to_sync.keys() if x in vals.keys()]
                    vals_order_line = {}
                    for field in sync:
                        vals_order_line[fields_to_sync[field]] = vals[field]
                    line.sale_line_ids.with_context(force_price=True).write(vals_order_line)
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
        # Cette fonction n'a encore jamais été appelée
        if not self.env['ir.values'].get_default('sale.config.settings', 'bool_vers_selection_fait'):
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
        help=u"Catégorie des articles utilisés pour les acomptes"
    )

    stock_warning_setting = fields.Boolean(
        string="(OF) Stock", required=True, default=False,
        help=u"Afficher les messages d'avertissement de stock ?"
    )

    pdf_display_product_ref_setting = fields.Boolean(
        string=u"(OF) Réf. produits", required=True, default=False,
        help=u"Afficher les références produits dans les rapports PDF ?"
    )

    pdf_date_validite_devis = fields.Boolean(
        string=u"(OF) Date validité devis", required=True, default=False,
        help=u"Afficher la date de validité dans le rapport PDF des devis ?"
    )

    pdf_vt_pastille = fields.Boolean(
        string=u"(OF) Date VT pastille", required=True, default=False,
        help=u"Afficher la date de visite technique dans une pastille dans le rapport PDF des devis ?"
    )

    pdf_adresse_nom_parent = fields.Boolean(
        string=u"(OF) Nom parent contact", required=True, default=False,
        help=u"Afficher le nom du 'parent' du contact au lieu du nom du contact dans les rapport PDF ?"
    )
    pdf_adresse_civilite = fields.Boolean(
        string=u"(OF) Civilités", required=True, default=False,
        help=u"Afficher la civilité dans les rapport PDF ?"
    )
    pdf_adresse_telephone = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Téléphone",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_adresse_mobile = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Mobile",
        help=u"Où afficher le numéro de téléphone mobile dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_adresse_fax = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) Fax",
        help=u"Où afficher le fax dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_adresse_email = fields.Selection(
        [
            (1, u"Afficher dans l'encart d'adresse principal"),
            (2, u"Afficher dans une pastille d'informations complémentaires"),
            (3, u"Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) E-mail",
        help=u"Où afficher l'adresse email dans les rapport PDF ? Ne rien mettre pour ne pas afficher."
    )
    pdf_afficher_multi_echeances = fields.Boolean(
        string=u"(OF) Multi-échéances", required=True, default=False,
        help=u"Afficher les échéances multiples dans les rapports PDF ?"
    )
    of_color_bg_section = fields.Char(
        string="(OF) Couleur fond titres section",
        help=u"Choisissez un couleur de fond pour les titres de section", default="#F0F0F0"
    )

    of_position_fiscale = fields.Boolean(string="(OF) Position fiscale")

    @api.multi
    def set_pdf_adresse_nom_parent_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_nom_parent', self.pdf_adresse_nom_parent)

    @api.multi
    def set_pdf_adresse_civilite_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_civilite', self.pdf_adresse_civilite)

    @api.multi
    def set_pdf_adresse_telephone_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_telephone', self.pdf_adresse_telephone)

    @api.multi
    def set_pdf_adresse_mobile_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_mobile', self.pdf_adresse_mobile)

    @api.multi
    def set_pdf_adresse_fax_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_fax', self.pdf_adresse_fax)

    @api.multi
    def set_pdf_adresse_email_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_adresse_email', self.pdf_adresse_email)

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
    def set_pdf_vt_pastille_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_vt_pastille', self.pdf_vt_pastille)

    @api.multi
    def set_of_deposit_product_categ_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_deposit_product_categ_id_setting', self.of_deposit_product_categ_id_setting.id)

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_color_bg_section', self.of_color_bg_section)

    @api.multi
    def set_pdf_afficher_multi_echeances_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_afficher_multi_echeances', self.pdf_afficher_multi_echeances)

    @api.multi
    def set_of_position_fiscale(self):
        view = self.env.ref('of_sale.of_sale_order_form_fiscal_position_required')
        if view:
            view.write({'active': self.of_position_fiscale})
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_position_fiscale',
            self.of_position_fiscale)


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ["account.invoice", "of.documents.joints"]

    @api.model
    def _of_function_active_picking(self):
        """
        Fonction appelée lors de la mise à jour du module.
        Détermine l'activation de la vue liée aux bons de livraison dans le formulaire des factures.
        """
        view = self.env.ref('of_sale.of_account_invoice_picking_view_form')
        if view:
            view.write({
                'active': self.env['ir.values'].get_default('account.config.settings', 'of_validate_pickings') in (2, 3)
            })

    of_date_vt = fields.Date(string="Date visite technique")
    of_sale_order_ids = fields.Many2many('sale.order', compute="_compute_of_sale_order_ids", string="Bons de commande")
    of_residual = fields.Float(
        string=u"Somme du montant non payé des factures d'acompte et de la facture finale",
        compute="_compute_of_residual")
    of_residual_equal = fields.Boolean(compute="_compute_of_residual")
    of_suivi_interne = fields.Char(string="Suivi interne")
    of_is_locked = fields.Boolean(compute="_compute_of_is_locked")
    of_waiting_delivery = fields.Boolean(string="Livraison en attente", compute="_compute_of_picking_ids")
    of_picking_ids = fields.Many2many('stock.picking', compute='_compute_of_picking_ids')
    of_picking_count = fields.Integer(string="Bon de livraisons", compute='_compute_of_picking_ids')

    @api.depends('invoice_line_ids')
    def _compute_of_sale_order_ids(self):
        for invoice in self:
            invoice.of_sale_order_ids = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')

    @api.depends('invoice_line_ids')
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
            invoice.of_residual_equal = invoice.state == 'draft' or \
                                        float_compare(invoice.of_residual, invoice.residual, 2) == 0

    @api.depends('invoice_line_ids', 'invoice_line_ids.of_is_locked')
    def _compute_of_is_locked(self):
        for invoice in self:
            if invoice.invoice_line_ids == invoice.invoice_line_ids.filtered('of_is_locked'):
                invoice.of_is_locked = True

    @api.multi
    @api.depends('invoice_line_ids', 'invoice_line_ids.sale_line_ids', 'invoice_line_ids.sale_line_ids.order_id',
                 'invoice_line_ids.sale_line_ids.order_id.picking_ids')
    def _compute_of_picking_ids(self):
        """
        Calcule le nombre de BL liés à la facture.
        :return:
        """
        for invoice in self:
            pickings = invoice.of_sale_order_ids.mapped('picking_ids')
            if pickings:
                invoice.of_waiting_delivery = pickings.filtered(lambda p: p.state not in ['draft', 'cancel', 'done'])\
                                              and True or False
                invoice.of_picking_ids = pickings
                invoice.of_picking_count = len(pickings)

    @api.multi
    def validate_pickings(self):
        transfer_obj = self.env['stock.immediate.transfer']
        for invoice in self.filtered(lambda i: not i.of_is_locked):
            pickings = invoice.of_picking_ids
            # force_assign() ne fonctionne pas bien si des articles sont déjà considérés comme fait
            pickings.pack_operation_product_ids.write({'qty_done': 0.0})
            pickings.force_assign()
            for picking in pickings:
                new_transfer = transfer_obj.create({'pick_id': picking.id})
                new_transfer.process()
        self._compute_of_picking_ids()

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
        if self.env['ir.values'].get_default('account.config.settings', 'of_validate_pickings') == 3:
            self.validate_pickings()
        return res

    @api.multi
    def action_view_delivery(self):
        """
        Afficher les BL liés à la facture
        :return:
        """
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('of_picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    @api.multi
    def _of_get_linked_invoices(self):
        """ [IMPRESSION]
        Retourne les factures liées à la facture courante.
        Les factures liées sont celles dont une ligne est liée à la même ligne de commande qu'une ligne de lines.
        Toute facture liée à une facture liée est également retournée.
        """
        invoice_obj = self.env['account.invoice']
        self.ensure_one()
        if self.type != 'out_invoice':
            return self
        group_paiements = self.env['of.invoice.report.total.group'].get_group_paiements()
        if not (group_paiements and group_paiements.invoice):
            # Le groupe des paiements n'est pas coniguré pour les factures.
            return self

        group_paiements_lines = group_paiements.filter_lines(self.invoice_line_ids, self)
        if group_paiements_lines is False:
            # Aucune ligne de la facture n'est à considérer comme un paiement.
            return self

        invoices = self
        to_check = (group_paiements_lines
                    .mapped('sale_line_ids')
                    .mapped('invoice_lines')
                    .mapped('invoice_id')
                    .filtered(lambda i: i.state != 'cancel'))
        while to_check:
            invoices |= to_check
            to_check = (to_check
                        .mapped('invoice_line_ids')
                        .mapped('sale_line_ids')
                        .mapped('invoice_lines')
                        .mapped('invoice_id')
                        .filtered(lambda i: i.state != 'cancel')) - invoices

        refunds = invoices.filtered(lambda inv: inv.type != self.type)
        invoices -= refunds
        for refund in refunds:
            # On fait abstraction des factures annulées par des avoirs
            move_ids = refund.payment_move_line_ids.mapped('move_id')
            if len(move_ids) == 1:
                invoice = invoices.filtered(
                    lambda inv: inv.move_id == move_ids and inv.amount_total == refund.amount_total)
                if invoice:
                    if invoice == self:
                        # La facture en cours est annulée par un avoir
                        return self
                    invoices -= invoice

        # On ne garde que les factures dont toutes les lignes sont contrebalancées
        order_lines = invoices.mapped('invoice_line_ids').mapped('sale_line_ids')
        while order_lines:
            invs_to_remove = invoice_obj
            for order_line in order_lines:
                invs = order_line.invoice_lines.mapped('invoice_id').filtered(lambda inv: inv in invoices)
                if len(invs) == 1 and invs != self:
                    invs_to_remove |= invs
            invoices -= invs_to_remove
            order_lines = invs_to_remove.mapped('invoice_line_ids').mapped('sale_line_ids')

        # Tri dans l'ordre
        invoices = invoice_obj.search([('id', 'in', invoices.ids)])
        return invoices

    @api.multi
    def _of_get_printable_payments(self):
        """ [IMPRESSION]
        Renvoie les lignes à afficher.
        """
        account_move_line_obj = self.env['account.move.line']

        # Retour de tous les paiements des factures
        # On distingue les paiements de la facture principale de ceux des factures liées
        result_dict = {}
        for invoice in self:
            widget = json.loads(invoice.payments_widget.replace("'", "\'"))
            if not widget:
                continue
            for payment in widget.get('content', []):
                # Les paiements sont classés dans l'ordre chronologique
                sort_key = (payment['date'], invoice.date_invoice, invoice.number, payment['payment_id'])
                move_line = account_move_line_obj.browse(payment['payment_id'])
                name = self._of_get_payment_display(move_line)
                result_dict[sort_key] = (name, payment['amount'])
        result = [result_dict[key] for key in sorted(result_dict)]
        return result

    @api.multi
    def _of_get_recap_taxes(self, invoices):
        """ [IMPRESSION]
        Retourne la liste des taxes à afficher dans le récapitulatif de la facture pdf.
        """
        tax_vals = []
        taxes = {}
        round_curr = self.currency_id.round
        inv_type = self.type
        for inv in invoices:
            sign = inv.type == inv_type or -1
            for inv_tax in inv.tax_line_ids:
                tax = inv_tax.tax_id
                if tax in taxes:
                    vals = taxes[tax]
                    vals[1] += inv_tax.base * sign
                    vals[2] += inv_tax.amount * sign
                else:
                    vals = [tax.description, inv_tax.base * sign, inv_tax.amount * sign]
                    tax_vals.append(vals)
                    taxes[tax] = vals
        for vals in tax_vals:
            vals[1] = round_curr(vals[1])
            vals[2] = round_curr(vals[2])
        return [vals for vals in tax_vals if vals[1]]

    @api.multi
    def of_get_printable_data(self):
        result = super(AccountInvoice, self).of_get_printable_data()
        report_pages_full = self.order_lines_layouted()
        report_lines = result['lines']
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
        result['lines_layouted'] = report_pages
        return result

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Surcharge pour que tout avoir soit pris en compte dans la commande
        """
        result = super(AccountInvoice, self)._refund_cleanup_lines(lines)
        if self.env.context.get('of_mode') == 'cancel':
            for i in xrange(0, len(lines)):
                for name, field in lines[i]._fields.iteritems():
                    if name == 'sale_line_ids':
                        result[i][2][name] = [(6, 0, lines[i][name].ids)]
        return result

    def pdf_vt_pastille(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_vt_pastille')


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    pdf_vt_pastille = fields.Boolean(
        string=u"(OF) Date VT pastille", required=True, default=False,
        help=u"Afficher la date de visite technique dans une pastille dans le rapport PDF des factures ?")

    of_color_bg_section = fields.Char(
        string="(OF) Couleur fond titres section", help=u"Choisissez une couleur de fond pour les titres de section",
        default="#F0F0F0")
    of_validate_pickings = fields.Selection([
            (1, u"Ne pas gérer les BL depuis la facture"),
            (2, u"Gérer les BL après la validation de la facture"),
            (3, u"Valider les BL au moment de la validation de la facture")],
        string="(OF) Validation des BL",
        default=1)

    @api.multi
    def set_pdf_vt_pastille_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_vt_pastille', self.pdf_vt_pastille)

    @api.multi
    def set_of_color_bg_section_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'of_color_bg_section', self.of_color_bg_section)

    @api.multi
    def set_of_validate_pickings(self):
        view = self.env.ref('of_sale.of_account_invoice_picking_view_form')
        if view:
            view.write({'active': self.of_validate_pickings in (2, 3)})
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_validate_pickings',
                                                        self.of_validate_pickings)


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


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_invoice_policy = fields.Selection(
        [('order', u'Quantités commandées'), ('delivery', u'Quantités livrées')],
        string="Politique de facturation")


class ProductCategory(models.Model):
    _inherit = 'product.category'

    of_article_principal = fields.Boolean(string="Article principal",
                                          help=u"Les articles de cette catégorie seront considérés comme articles"
                                               u" principaux sur les commandes / factures clients")


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.multi
    def of_is_quantity_dependent(self, product_id, date_eval=fields.Date.today()):
        u"""
            :param: product_id Produit évalué
            :param: date_eval Date d'évaluation de la liste de prix
            :return: True si le produit évalué est contenu dans cette liste et que son prix dépend de la quantité
        """
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        for item in self.item_ids:
            if item.min_quantity and item.min_quantity > 1:
                # une date de début pour cet item et la date d'évaluation antérieure à cette date de début
                if item.date_start and date_eval < item.date_start:
                    continue
                # une date de fin pour cet item et la date d'évaluation postérieure à cette date de fin
                if item.date_end and date_eval > item.date_end:
                    continue
                # l'item s'applique sur une catégorie d'article différente de celle de l'article évalué
                if item.applied_on == '2_product_category' and item.categ_id \
                        and item.categ_id != product.product_tmpl_id.categ_id:
                    continue
                # l'item s'applique sur un article différent de l'article évalué
                if item.applied_on == '1_product' and item.product_tmpl_id \
                        and item.product_tmpl_id != product.product_tmpl_id:
                    continue
                # l'item s'applique sur une variante différente de la variante évaluée
                if item.applied_on == '0_product_variant' and item.product_id and item.product_id != product:
                    continue
                return True
        return False


class OFOrderLineOption(models.Model):
    _name = 'of.order.line.option'
    _description = u"Option pour les lignes de commande (Achat et Vente)"

    name = fields.Char(string=u"Nom", required=True)
    purchase_price_update = fields.Boolean(string=u"Modification du prix d'achat")
    purchase_price_update_type = fields.Selection(
        selection=[('fixed', u"Montant fixe"),
                   ('percent', u"Pourcentage")], string=u"Type de modification du prix d'achat")
    purchase_price_update_value = fields.Float(string=u"Valeur de modification du prix d'achat")
    sale_price_update = fields.Boolean(string=u"Modification du prix de vente")
    sale_price_update_type = fields.Selection(
        selection=[('fixed', u"Montant fixe"),
                   ('percent', u"Pourcentage")], string=u"Type de modification du prix de vente")
    sale_price_update_value = fields.Float(string=u"Valeur de modification du prix de vente")
    description_update = fields.Text(string=u"Description de la ligne de commande")


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        res = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)

        # Prise en compte de l'option de ligne de commande
        sale_line = self.sale_line_id
        if not sale_line:
            sale_line = self.move_dest_id.procurement_id.sale_line_id
        if sale_line and sale_line.of_order_line_option_id:
            option = sale_line.of_order_line_option_id
            res['of_order_line_option_id'] = option.id
            if option.purchase_price_update and res['price_unit']:
                if option.purchase_price_update_type == 'fixed':
                    res['price_unit'] = res['price_unit'] + option.purchase_price_update_value
                elif option.purchase_price_update_type == 'percent':
                    res['price_unit'] = res['price_unit'] + (res['price_unit'] *
                                                             (option.purchase_price_update_value / 100))
                res['price_unit'] = po.currency_id.round(res['price_unit'])

        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    of_order_line_option_id = fields.Many2one(comodel_name='of.order.line.option', string=u"Option")

    @api.onchange('of_order_line_option_id')
    def _onchange_of_order_line_option_id(self):
        if self.of_order_line_option_id and self.product_id:
            option = self.of_order_line_option_id
            if option.purchase_price_update and self.price_unit:
                if option.purchase_price_update_type == 'fixed':
                    self.price_unit = self.price_unit + option.purchase_price_update_value
                elif option.purchase_price_update_type == 'percent':
                    self.price_unit = self.price_unit + (self.price_unit * (option.purchase_price_update_value / 100))
                self.price_unit = self.order_id.currency_id.round(self.price_unit)
            self.name = self.name + "\n%s" % option.description_update
