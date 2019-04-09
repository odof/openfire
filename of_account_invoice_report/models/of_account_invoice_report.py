# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

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
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_telephone')

    def pdf_afficher_mobile(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_mobile')

    def pdf_afficher_fax(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_fax')

    def pdf_afficher_email(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_adresse_email')

    @api.multi
    def _of_get_total_lines_by_group(self):
        """
        Retourne les lignes de la facture, séparées en fonction du groupe dans lequel les afficher.
        Les groupes sont ceux définis par l'objet of.invoice.report.total, permettant de déplacer le rendu des
          lignes de facture sous le total TTC.
        Les groupes sont affichés dans leur ordre propre, puis les lignes dans l'ordre de leur apparition dans la facture.
        @param return: Liste de couples (groupe, lignes de facture). Le premier élément vaut (False, Lignes non groupées).
        """
        self.ensure_one()
        group_obj = self.env['of.invoice.report.total.group']

        lines = self.invoice_line_ids
        products = lines.mapped('product_id')
        product_ids = list(products._ids)
        categ_ids = list(products.mapped('categ_id')._ids)
        groups = group_obj.search([('invoice', '=', True),
                                   '|', ('id', '=', group_obj.get_group_paiements().id),
                                   '|', ('product_ids', 'in', product_ids), ('categ_ids', 'in', categ_ids)])

        result = []
        # Le groupe des paiements peut absorber des lignes d'autres groupes.
        # Il faut donc le traiter en priorité.
        for group in groups:
            if group.is_group_paiements():
                group_paiement_lines = group.filter_lines(lines)
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
            result = [(False, self.invoice_line_ids)]
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

    @api.model
    def _of_get_payment_display(self, move_line):
        """ [IMPRESSION]
        Détermine le descriptif à afficher pour un paiement
        """
        return _('<i>Paid on %s</i>') % (move_line.date)

    @api.multi
    def _of_get_printable_payments(self, lines):
        """ [IMPRESSION]
        Renvoie les lignes à afficher
        """
        account_move_line_obj = self.env['account.move.line']
        result = []
        for payment in json.loads(self.payments_widget.replace("'", "\'")).get('content', []):
            move_line = account_move_line_obj.browse(payment['payment_id'])
            name = self._of_get_payment_display(move_line)
            result.append((name, payment['amount']))
        return result

    @api.multi
    def _of_get_printable_totals(self):
        """ [IMPRESSION]
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
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
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
    pdf_display_product_ref = fields.Boolean(
        string="(OF) Réf. produits", required=True, default=False,
        help="Afficher les références produits dans les rapports PDF ?")

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
        readonly=True, help=u"Fonctionnalité en cours de développement")
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
    def filter_lines(self, lines):
        """
        Filtre les lignes reçues en fonction des articles/catégories autorisés pour le groupe courant.
        """
        self.ensure_one()
        if self.is_group_paiements():
            # On n'autorise pas d'articles dans les paiements. (Voir module of_sale pour cette possibilité)
            return lines.browse([])
        return lines.filtered(lambda l: (l.product_id in self.product_ids or
                                         l.product_id.categ_id in self.categ_ids)) or False
