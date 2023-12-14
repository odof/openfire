# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import itertools
import json
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import formatLang



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

    def pdf_masquer_commercial(self):
        return self.env['ir.values'].get_default('account.config.settings', 'pdf_masquer_pastille_commercial')

    def pdf_pastille_payment_term(self):
        return self.env['ir.values'].get_default('account.config.settings', 'of_pdf_pastille_payment_term')

    def pdf_payment_schedule(self):
        return self.env['ir.values'].get_default('account.config.settings', 'of_payment_schedule')

    @api.multi
    def _of_get_total_lines_by_group(self, invoices):
        u"""
        Retourne les lignes de la facture, séparées en fonction du groupe dans lequel les afficher.
        Les groupes sont ceux définis par l'objet of.invoice.report.total, permettant de déplacer le rendu des
          lignes de facture sous le total TTC.
        Les groupes sont affichés dans leur ordre propre,
        puis les lignes dans l'ordre de leur apparition dans la facture.
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
        payments = json.loads(self.payments_widget.replace("'", "\'"))
        for payment in payments and payments.get('content') or []:
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
            r[0].name,
            r[1],
            formatLang(self.with_context(lang=self[0].partner_id.lang).env, r[1], currency_obj=currency)
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
        return [[result, (_("Total TTC"), round_curr(total_amount))]]

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
            if group.hide_amount_total and len(result['taxes'][0]) == 2:
                result['taxes'][0].pop(1)
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
