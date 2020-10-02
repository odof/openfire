# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import formatLang

import json


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    # Note : les fonctions de cette classe qui possèdent [IMPRESSION] dans leur description
    # ne sont appelées que lors de l'impression.

    def pdf_afficher_nom_parent(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_nom_parent')

    def pdf_afficher_civilite(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_civilite')

    def pdf_afficher_telephone(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_telephone') or 0

    def pdf_afficher_mobile(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_mobile') or 0

    def pdf_afficher_fax(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_fax') or 0

    def pdf_afficher_email(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_email') or 0

    def pdf_mention_legale(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_mention_legale') or ""

    @api.multi
    def _of_get_total_lines_by_group(self, invoices):
        u"""
        Retourne les lignes de la facture, séparées en fonction du groupe dans lequel les afficher.
        Les groupes sont ceux définis par l'objet of.invoice.report.total, permettant de déplacer le rendu des
          lignes de facture sous le total TTC.
        Les groupes sont affichés dans leur ordre propre, puis les lignes dans l'ordre de leur apparition dans la facture.
        :param invoices: Ensemble des factures à utiliser pour générer le document.
        :return: Liste de couples (groupe, lignes de facture). Le premier élément vaut (False, Lignes non groupées).
        """
        self.ensure_one()
        group_obj = self.env['of.invoice.report.total.group']

        lines = self.invoice_line_ids
        products = lines.mapped('product_id')
        product_ids = products.ids
        categ_ids = products.mapped('categ_id').ids
        groups = group_obj.search([('invoice', '=', True),
                                   '|', ('id', '=', group_obj.get_group_paiements().id),
                                   '|', ('product_ids', 'in', product_ids), ('categ_ids', 'in', categ_ids)])

        result = []
        # Le groupe des paiements peut absorber des lignes d'autres groupes.
        # Il faut donc le traiter en priorité.
        group_paiement_lines = lines.browse([])
        for group in groups:
            if group.is_group_paiements():
                group_paiement_lines = group.filter_lines(lines, invoices-self)
                if group_paiement_lines is not False:
                    lines -= group_paiement_lines
                break

        # Séparation des lignes en groupes
        for group in groups:
            if group.is_group_paiements():
                result.append((group, group_paiement_lines))
            else:
                group_lines = group.filter_lines(lines)
                if group_lines is not False:
                    result.append((group, group_lines))
                    lines -= group_lines

        if lines:
            result = [(False, lines)] + result
        else:
            result = [(False, self.invoice_line_ids - group_paiement_lines)]
            # On ajoute quand-même les paiements
            for group in groups:
                if group.is_group_paiements():
                    # Les lignes de paiements doivent rester dans le groupe des paiements.
                    result.append((group, group_paiement_lines))
        return result

    @api.multi
    def of_get_printable_data(self):
        u"""[IMPRESSION]
        Fonction de calcul des données à imprimer dans la facture pdf.
        Ces données incluent les lignes de facture, les totaux et le récapitulatif des taxes.
        :return: Dictionnaire de données à imprimer dans la facture pdf.
        """
        self.ensure_one()
        invoices = self._of_get_linked_invoices()
        group_lines = self._of_get_total_lines_by_group(invoices)
        return {
            'lines': group_lines[0][1],
            'totals': self._of_get_printable_totals(invoices, group_lines),
            'taxes': self._of_get_recap_taxes(invoices)
        }

    @api.model
    def _of_get_payment_display(self, move_line):
        u"""[IMPRESSION]
        Détermine le descriptif à afficher pour un paiement.
        Cette fonction a pour but d'être surchargée dans of_account_payment_mode.

        :param move_line: Écriture comptable du paiement.
        :return: Texte à afficher pour le paiement.
        """
        return _('<i>Paid on %s</i>') % (move_line.date)

    @api.multi
    def _of_get_printable_payments(self):
        u"""[IMPRESSION]
        Cette fonction a pour but d'être surchargée dans of_sale pour récupérer tous les paiements
          liés à la commande d'origine.

        :param lines:
        :return: Lignes de paiement à afficher dans la facture.
        :rtype: Liste de tuples [(libellé: montant)]
        """
        account_move_line_obj = self.env['account.move.line']
        result = []
        for payment in json.loads(self.payments_widget.replace("'", "\'")).get('content', []):
            move_line = account_move_line_obj.browse(payment['payment_id'])
            name = self._of_get_payment_display(move_line)
            result.append((name, payment['amount']))
        return result

    @api.multi
    def _of_get_tax_amount_by_group(self):
        u""" [IMPRESSION]
        Fonction identique à la fonction _get_tax_amount_by_group,
        mais permet l'agglomération des taxes de plusieurs factures passées en paramètre.
        """
        res = {}
        currency = self[0].currency_id or self[0].company_id.currency_id
        inv_type = self[0].type
        for invoice in self:
            sign = invoice.type == inv_type or -1
            for line in invoice.tax_line_ids:
                res.setdefault(line.tax_id.tax_group_id, 0.0)
                res[line.tax_id.tax_group_id] += line.amount * sign
        res = sorted(res.items(), key=lambda l: l[0].sequence)
        res = [(
            r[0].name, r[1], formatLang(self.with_context(lang=self[0].partner_id.lang).env, r[1], currency_obj=currency)
        ) for r in res]
        return res

    @api.multi
    def _of_get_printable_taxes(self, total_amount):
        u""" [IMPRESSION]
        Renvoie les lignes à afficher.
        Cette fonction a pour but d'être surchargée dans of_sale pour récupérer toutes les taxes
          liées à la commande d'origine.
        """
        round_curr = self[0].currency_id.round
        result = []
        for tax in self._of_get_tax_amount_by_group():
            result.append((tax[0], tax[1]))
            total_amount += tax[1]
        return [[result, (_("Total"), round_curr(total_amount))]]

    @api.multi
    def _of_get_linked_invoices(self):
        u"""[IMPRESSION]
        Retourne les factures liées à la facture courante.
        Les factures liées sont celles dont une ligne est liée à la même ligne de commande qu'une ligne de lines.
        Toute facture liée à une facture liée est également retournée.
        :return: Factures associées à la facture courante (incluse) pour l'impression pdf.
        """
        self.ensure_one()
        return self

    @api.multi
    def _of_get_printable_totals(self, invoices, group_lines):
        u""" [IMPRESSION]
        Retourne un dictionnaire contenant les valeurs à afficher dans les totaux de la facture pdf.
        Dictionnaire de la forme :
        {
            'subtotal' : Total HT des lignes affichées,
            'untaxed' : [[('libellé', montant),...], ('libellé total': montant_total)]
            'taxes' : idem,
            'total' : idem,
        }
        Les listes untaxed, taxes et total pourraient être regroupés en une seule.
        Ce format pourra aider aux héritages (?).
        :param invoices: Ensemble des factures à utiliser pour générer le document.
        :param group_lines: Résultat de self._of_get_total_lines_by_group(invoices) afin d'éviter le recalcul.
        :return: Valeurs à afficher dans les totaux de la facture pdf.
        """
        self.ensure_one()
        round_curr = self.currency_id.round

        result = {'subtotal': sum(group_lines[0][1].mapped('price_subtotal'))}
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
        result['taxes'] = invoices._of_get_printable_taxes(total_amount)
        total_amount = result['taxes'][0][1][1]

        # --- Sous-totaux TTC ---
        result_total = []
        while i < len(group_lines):
            # Tri des paiements par date
            group, lines = group_lines[i]
            i += 1
            if group.is_group_paiements():
                lines_vals = invoices._of_get_printable_payments()
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
    def _of_get_recap_taxes(self, invoices):
        u""" [IMPRESSION]
        Retourne la liste des taxes à afficher dans le récapitulatif de la facture pdf.
        """
        self.ensure_one()
        return [(t.tax_id.description, t.base, t.amount)
                for t in self.tax_line_ids]


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


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    @api.model
    def _auto_init(self):
        """
        Certain paramètres d'affichage sont passés de Booléen à Sélection.
        Cette fonction est appelée à chaque mise à jour mais ne fait quelque chose que la première fois qu'elle est appelée.
        """
        set_value = False
        if not self.env['ir.values'].get_default('account.config.settings', 'bool_vers_selection_fait'):  # Cette fonction n'a encore jamais été appelée
            set_value = True
        super(AccountConfigSettings, self)._auto_init()
        if set_value:
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_telephone'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_telephone', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_telephone', 0)
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_mobile'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_mobile', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_mobile', 0)
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_fax'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_fax', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_fax', 0)
            if self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_email'):
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_email', 1)
            else:
                self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_email', 0)
            self.env['ir.values'].sudo().set_default('account.config.settings', 'bool_vers_selection_fait', True)

    pdf_adresse_nom_parent = fields.Boolean(
        string=u"(OF) Nom parent contact", required=True, default=False,
        help=u"Afficher le nom du 'parent' du contact au lieu du nom du contact dans les rapport PDF ?")
    pdf_adresse_civilite = fields.Boolean(
        string=u"(OF) Civilités", required=True, default=False,
        help=u"Afficher la civilité dans les rapport PDF ?")
    pdf_adresse_telephone = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Téléphone",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_mobile = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string=u"(OF) Mobile",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_fax = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) Fax",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_adresse_email = fields.Selection(
        [
            (1, "Afficher dans l'encart d'adresse principal"),
            (2, "Afficher dans une pastille d'informations complémentaires"),
            (3, "Afficher dans l'encart d'adresse principal et dans une pastille d'informations complémentaires")
        ], string="(OF) E-mail",
        help=u"Où afficher le numéro de téléphone dans les rapport PDF ? Ne rien mettre pour ne pas afficher.")
    pdf_display_product_ref = fields.Boolean(
        string="(OF) Réf. produits", required=True, default=False,
        help="Afficher les références produits dans les rapports PDF ?")

    pdf_mention_legale = fields.Text(
        string=u"(OF) Mentions légales", help=u"Sera affiché dans les factures sous les commentaires du bas"
    )

    @api.multi
    def set_pdf_adresse_nom_parent_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_nom_parent', self.pdf_adresse_nom_parent)

    @api.multi
    def set_pdf_adresse_civilite_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_civilite', self.pdf_adresse_civilite)

    @api.multi
    def set_pdf_adresse_telephone_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_telephone', self.pdf_adresse_telephone)

    @api.multi
    def set_pdf_adresse_mobile_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_mobile', self.pdf_adresse_mobile)

    @api.multi
    def set_pdf_adresse_fax_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_fax', self.pdf_adresse_fax)

    @api.multi
    def set_pdf_adresse_email_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_adresse_email', self.pdf_adresse_email)

    @api.multi
    def set_pdf_display_product_ref_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'pdf_display_product_ref', self.pdf_display_product_ref)

    @api.multi
    def set_pdf_mention_legale_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'pdf_mention_legale', self.pdf_mention_legale
        )


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
