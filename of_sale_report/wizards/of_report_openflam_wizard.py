# -*- coding: utf-8 -*-

import base64
from datetime import datetime
from odoo import models, fields, api
from odoo.tools import float_compare

from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range


class OFRapportOpenflamWizard(models.TransientModel):
    _name = 'of.rapport.openflam.wizard'
    _description = 'Rapport Openflam'

    @api.model
    def _get_allowed_report_types(self):
        param_rapport_sur_mesure = self.env['ir.values'].get_default('sale.config.settings', 'of_rapport_sur_mesure')
        result = []
        if param_rapport_sur_mesure != 'fabricant':
            result.append(('encours', u"État des encours de commandes de vente"))
            result.append(('echeancier', u"Échéancier des règlements fournisseurs"))
        if param_rapport_sur_mesure != 'revendeur':
            result.append(('stats', "Statistiques de ventes"))
            result.append(('encaissement', "TVA sur encaissement"))
        return result

    file_name = fields.Char('Nom du fichier', size=64)
    file = fields.Binary('file')
    company_ids = fields.Many2many('res.company', string=u'Sociétés')
    user_company_id = fields.Many2one('res.company', compute="_compute_company_id")
    date = fields.Date(u'Date de création', default=datetime.now().strftime("%Y-%m-%d"))
    report_model = fields.Selection(_get_allowed_report_types, string=u"Modèle de rapport", required=True)
    period_n = fields.Many2one('date.range', string=u"Période")
    period_n1 = fields.Many2one('date.range', string=u"Période")
    product_ids = fields.Many2many('product.template', string="Articles")
    partner_ids = fields.Many2many('res.partner', string="Clients")
    category_ids = fields.Many2many('product.category', string=u"Catégories d'articles")
    stats_partner = fields.Boolean(string="Stats/articles/clients", default=True)
    stats_product = fields.Boolean(string=u"Stats/clients/catégories d'articles", default=True)
    filtre_client = fields.Boolean(string="Filtre par client")
    filtre_article = fields.Boolean(string="Filtre par article")

    debut_n = fields.Date(string=u"Début")
    fin_n = fields.Date(string="Fin")
    debut_n1 = fields.Date(string=u"Début")
    fin_n1 = fields.Date(string="Fin")
    type_filtre_date = fields.Selection(
        [('period', u'Périodes'), ('date', 'Dates')], string="Type de filtre", default="period")
    brand_ids = fields.Many2many('of.product.brand', string="Marques")
    stats_brand = fields.Boolean(string="Stats/marques/clients", default=True)
    etiquette_ids = fields.Many2many('res.partner.category', string=u"Étiquettes clients")

    @api.depends('report_model')
    def _compute_company_id(self):
        user_obj = self.env['res.users']
        user = user_obj.browse(self._uid)
        self.user_company_id = user.company_id

    @api.multi
    def _dummy_function(self):
        self.file = False
        return {"type": "ir.actions.do_nothing"}

    @api.model
    def _get_styles_excel(self, workbook):
        # color_light_gray = '#C0C0C0'
        color_lighter_gray = '#DDDDDD'
        color_light_blue = '#66FFFF'
        color_light_yellow = '#FFFB1C'
        color_red = '#800000'

        style_text_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'font_size': 10,
        })

        style_text_border_left = workbook.add_format({
            'valign': 'vcenter',
            'align': 'left',
            'border': 1,
            'font_size': 10,
        })

        style_text_bold_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 10,
        })

        style_text_title_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_lighter_gray,
        })

        style_text_title_border_blue = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_light_blue,
        })

        style_text_title_border_blue_left = workbook.add_format({
            'valign': 'vcenter',
            'align': 'left',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_light_blue,
        })

        style_text_title_border_yellow = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_light_yellow,
        })

        style_text_title_border_red = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 13.5,
            'bg_color': color_lighter_gray,
            'font_color': color_red,
        })

        style_text_title_border_wrap = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'text_wrap': True,
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_lighter_gray,
        })

        style_text_title_ita_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'italic': True,
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_lighter_gray,
        })

        style_text_total_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'left',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_lighter_gray,
        })

        style_number_border = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 8,
            'border': True,
        })

        style_number_border_yellow = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 8,
            'border': True,
            'bg_color': color_light_yellow,
        })

        style_number_border_percent = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00 %',
            'font_size': 8,
            'border': True,
        })

        style_number_bold_border = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 8,
            'border': True,
            'bold': True,
        })

        style_number_title_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_lighter_gray,
            'num_format': '#,##0.00',
        })

        style_number_title_border_blue = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_light_blue,
            'num_format': '#,##0.00',
        })

        style_number_title_border_blue_percent = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_light_blue,
            'num_format': '#,##0.00 %',
        })

        style_number_title_border_red = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_red,
            'num_format': '#,##0.00',
        })

        style_number_title_border_yellow = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_light_yellow,
            'num_format': '#,##0.00',
        })

        style_number_total_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_lighter_gray,
            'num_format': '#,##0.00',
        })

        return {
            'text_border': style_text_border,
            'text_border_left': style_text_border_left,
            'text_bold_border': style_text_bold_border,
            'text_title_border': style_text_title_border,
            'text_title_border_blue': style_text_title_border_blue,
            'text_title_border_yellow': style_text_title_border_yellow,
            'text_title_border_blue_left': style_text_title_border_blue_left,
            'text_title_border_red': style_text_title_border_red,
            'text_title_ita_border': style_text_title_ita_border,
            'text_title_border_wrap': style_text_title_border_wrap,
            'text_total_border': style_text_total_border,
            'number_border': style_number_border,
            'number_border_yellow': style_number_border_yellow,
            'number_border_percent': style_number_border_percent,
            'number_bold_border': style_number_bold_border,
            'number_title_border': style_number_title_border,
            'number_title_border_blue': style_number_title_border_blue,
            'number_title_border_blue_percent': style_number_title_border_blue_percent,
            'number_title_border_red': style_number_title_border_red,
            'number_title_border_yellow': style_number_title_border_yellow,
            'number_total_border': style_number_total_border,
        }

    @api.multi
    def _create_encours_excel(self):
        # --- Ouverture du workbook ---
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})

        # --- Récupération de styles ---
        styles = self._get_styles_excel(workbook)

        # --- Création de la page ---
        worksheet = workbook.add_worksheet(self.file_name.split('.')[0])
        worksheet.set_paper(9)  # Format d'impression A4
        worksheet.set_landscape()  # Format d'impression paysage
        worksheet.set_margins(left=0.35, right=0.35, top=0.2, bottom=0.2)

        # --- Initialisation des colonnes ---
        worksheet.set_column(0, 0, 13)      # Largeur colonne 'Date CC'
        worksheet.set_column(1, 1, 13)      # Largeur colonne 'n° CC'
        worksheet.set_column(2, 2, 16)      # Largeur colonne 'Pose prévisionnelle'
        worksheet.set_column(3, 3, 20)      # Largeur colonne 'Nom client'
        worksheet.set_column(4, 4, 16)      # Largeur colonne 'Vendeur'
        worksheet.set_column(5, 5, 16)      # Largeur colonne 'Total HT'
        worksheet.set_column(6, 6, 16)      # Largeur colonne 'Total TTC'
        worksheet.set_column(7, 7, 25)      # Largeur colonne 'Acompte(s) versé(s) (total)'
        worksheet.set_column(8, 8, 20)      # Largeur colonne 'Solde'

        # --- Entête ---
        worksheet.merge_range(0, 0, 0, 2, 'Nom du fichier', styles['text_title_ita_border'])
        worksheet.merge_range(0, 3, 0, 5, u'Date de création', styles['text_title_ita_border'])
        worksheet.merge_range(0, 6, 0, 8, u'Société(s)', styles['text_title_ita_border'])
        worksheet.merge_range(1, 0, 1, 2, self.file_name.split('.')[0], styles['text_title_border'])
        worksheet.merge_range(1, 3, 1, 5, self.date, styles['text_title_border'])
        worksheet.merge_range(1, 6, 1, 8, ", ".join(self.company_ids.mapped('name')), styles['text_title_border_wrap'])

        # --- Ajout des lignes ---
        line_number = 3
        worksheet.write(line_number, 0, 'Date CC', styles['text_title_border'])
        worksheet.write(line_number, 1, u'n° CC', styles['text_title_border'])
        worksheet.write(line_number, 2, u'Pose prévisionnelle', styles['text_title_border'])
        worksheet.write(line_number, 3, 'Nom du client', styles['text_title_border'])
        worksheet.write(line_number, 4, 'Vendeur', styles['text_title_border'])
        worksheet.write(line_number, 5, 'Total HT', styles['text_title_border'])
        worksheet.write(line_number, 6, 'Total TTC', styles['text_title_border'])
        worksheet.write(line_number, 7, u'Acompte(s) versé(s) (total)', styles['text_title_border'])
        worksheet.write(line_number, 8, 'solde', styles['text_title_border'])
        line_number += 1
        solde = 0
        week, total = [], []
        order_domain = [('state', 'in', ['sale', 'done'])]
        if self.company_ids._ids:
            order_domain = (order_domain and ['&']) + [('company_id', 'in', self.company_ids._ids)] + order_domain
        orders = self.env['sale.order'].search(order_domain).sorted(key=lambda r: r.of_date_de_pose)
        line_keep = line_number
        date = 0
        for order in orders:
            # --- Vérification du montant des acomptes ---
            payments = self.env['account.payment'].search([('communication', '=', order.name)])
            for invoice in order.invoice_ids:
                payments = payments | invoice.payment_ids
            montant_acomptes = sum(payment.amount for payment in payments)
            if montant_acomptes >= order.amount_total:
                continue

            # --- Ajout des lignes total de la semaine ---
            date = order.of_date_de_pose and fields.Datetime.from_string(order.of_date_de_pose).strftime("%W-%Y") or ''
            if not date and date not in week:
                week.append(date)
            if solde and date not in week:
                worksheet.merge_range(
                    line_number, 0, line_number, 4,
                    u'Total sans date de pose prévisionnelle' if date and week and not week[-1]
                    else 'Total de la semaine ' + week[-1],
                    styles['text_total_border'])
                week.append(date)
                for col in range(5, 9):
                    worksheet.write(
                        line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col),
                        styles['number_total_border'])
                total.append(line_number)
                line_number += 1
                line_keep = line_number

            # --- lignes régulières ---
            solde = order.amount_total - montant_acomptes
            worksheet.write(line_number, 0, order.date_order.split(' ')[0], styles['text_border'])
            worksheet.write(line_number, 1, order.name, styles['text_border'])
            worksheet.write(line_number, 2, order.of_date_de_pose or '', styles['text_border'])
            worksheet.write(line_number, 3, order.partner_id.name, styles['text_border'])
            worksheet.write(line_number, 4, order.user_id.name, styles['text_border'])
            worksheet.write(line_number, 5, order.amount_untaxed, styles['number_border'])
            worksheet.write(line_number, 6, order.amount_total, styles['number_border'])
            worksheet.write(line_number, 7, montant_acomptes, styles['number_border'])
            worksheet.write(line_number, 8, solde, styles['number_bold_border'])
            line_number += 1

        # --- Ajout de la ligne de la dernière semaine ---
        if solde:
            worksheet.merge_range(
                line_number, 0, line_number, 4,
                u'Total sans date de pose prévisionnelle' if not week[-1] and not date
                else 'Total de la semaine ' + week[-1],
                styles['text_total_border'])
            for col in range(5, 9):
                worksheet.write(
                    line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col),
                    styles['number_total_border'])
            total.append(line_number)
            line_number += 1

        # --- Ligne de récap total ---
        if solde and total:
            worksheet.merge_range(
                line_number, 0, line_number, 4, 'Total de toutes les semaines', styles['text_title_border'])
            for col in range(5, 9):
                val = '=%s' % ('+'.join([xl_rowcol_to_cell(x, col) for x in total]))
                worksheet.write(line_number, col, val, styles['number_title_border'])

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        return base64.b64encode(data)

    @api.multi
    def _create_echeancier_excel(self):
        # --- Ouverture du workbook ---
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})

        # --- Couleur de police ---
        styles = self._get_styles_excel(workbook)

        # --- Création de la page ---
        worksheet = workbook.add_worksheet(self.file_name.split('.')[0])
        worksheet.set_paper(9)  # Format d'impression A4
        worksheet.set_landscape()  # Format d'impression paysage
        worksheet.set_margins(left=0.35, right=0.35, top=0.2, bottom=0.2)

        # --- Initialisation des colonnes ---
        worksheet.set_column(0, 0, 13)      # Largeur colonne 'Date d'échéance'
        worksheet.set_column(1, 1, 20)      # Largeur colonne 'n° FF'
        worksheet.set_column(2, 2, 16)      # Largeur colonne 'Date FF'
        worksheet.set_column(3, 3, 20)      # Largeur colonne 'Fournisseur'
        worksheet.set_column(4, 4, 16)      # Largeur colonne 'Ref Fournisseur'
        worksheet.set_column(5, 5, 20)      # Largeur colonne 'conditions de règlement'
        worksheet.set_column(6, 6, 20)      # Largeur colonne 'Total HT'
        worksheet.set_column(7, 7, 20)      # Largeur colonne 'Total TTC'
        worksheet.set_column(8, 8, 25)      # Largeur colonne 'Acompte(s) versé(s)'
        worksheet.set_column(9, 9, 25)      # Largeur colonne 'Solde'

        # --- Entête ---
        worksheet.merge_range(0, 0, 0, 2, 'Nom du fichier', styles['text_title_ita_border'])
        worksheet.merge_range(0, 3, 0, 5, u'Date de création', styles['text_title_ita_border'])
        worksheet.merge_range(0, 6, 0, 8, u'Société(s)', styles['text_title_ita_border'])
        worksheet.merge_range(1, 0, 1, 2, self.file_name.split('.')[0], styles['text_title_border'])
        worksheet.merge_range(1, 3, 1, 5, self.date, styles['text_title_border'])
        worksheet.merge_range(1, 6, 1, 8, ", ".join(self.company_ids.mapped('name')), styles['text_title_border_wrap'])

        # --- Ajout des lignes ---
        line_number = 3
        worksheet.write(line_number, 0, u"Date d'échéance", styles['text_title_border'])
        worksheet.write(line_number, 1, u'n° FF', styles['text_title_border'])
        worksheet.write(line_number, 2, 'Date FF', styles['text_title_border'])
        worksheet.write(line_number, 3, 'Fournisseur', styles['text_title_border'])
        worksheet.write(line_number, 4, 'Ref Fournisseur', styles['text_title_border'])
        worksheet.write(line_number, 5, u'Conditions de règlement', styles['text_title_border'])
        worksheet.write(line_number, 6, 'Total HT', styles['text_title_border'])
        worksheet.write(line_number, 7, 'Total TTC', styles['text_title_border'])
        worksheet.write(line_number, 8, u'Acompte(s) versé(s) (total)', styles['text_title_border'])
        worksheet.write(line_number, 9, 'solde', styles['text_title_border'])
        line_number += 1
        solde = 0
        day, total = [], []
        move_domain = [('journal_id.type', '=', 'purchase')]
        if self.company_ids._ids:
            move_domain = ['&', ('company_id', 'in', self.company_ids._ids)] + move_domain
        moves = self.env['account.move'].search(move_domain, order='of_date_due DESC')
        move_line_obj = self.env['account.move.line']

        line_keep = line_number
        for move in moves:
            payment_line_ids = []
            # Lignes copiées de account.invoice._compute_payments()
            # payment_line_ids est la liste des ids de account.move.line représentant des paiements/avoirs.
            for line in move.line_ids.filtered('credit').filtered(
                    lambda ml: ml.account_id.user_type_id.type == 'payable'):
                payment_line_ids.extend(filter(None, [rp.debit_move_id.id for rp in line.matched_debit_ids]))
            # payments est la liste des account.partial.reconcile associés aux lignes de paiements/avoirs trouvées.
            payments = move_line_obj.browse(list(set(payment_line_ids))).mapped('matched_credit_ids')

            # --- Vérification du montant des acomptes ---
            # Calcul adapté de celui des payments_widget des factures
            # filt est la liste des lettrages entre écritures de paiements/avoirs et écritures de facture.
            filt = payments.filtered(lambda ml: ml.credit_move_id.id in move.line_ids._ids)
            montant_acomptes = sum([p.amount for p in filt])
            amount_total = sum(
                move.line_ids.filtered(lambda ml: ml.account_id.user_type_id.type == 'payable').mapped('credit'))
            if move.currency_id.round(montant_acomptes) >= move.currency_id.round(amount_total):
                continue

            # --- Ajout des lignes total de la semaine ---
            date_due = move.of_date_due
            date = date_due and fields.Datetime.from_string(date_due).strftime("%Y-%m-%d") or ''
            if not day:
                day.append(date)
            if solde and date not in day:
                worksheet.merge_range(
                    line_number, 0, line_number, 5,
                    u"Total sans date d'échéance" if date and not day[-1]
                    else u"Total de la date d'échéance " + day[-1],
                    styles['text_total_border'])
                day.append(date)
                for col in range(6, 10):
                    worksheet.write(
                        line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col),
                        styles['number_total_border'])
                total.append(line_number)
                line_number += 1
                line_keep = line_number

            line_taxes = move.line_ids.filtered(lambda ml: ml.account_id.code.startswith('445'))
            taxes = sum(line_taxes.mapped('debit')) - sum(line_taxes.mapped('credit'))

            payment_term = False
            invoice = move.line_ids.mapped('invoice_id')
            if len(invoice) == 1:
                payment_term = invoice.payment_term_id

            # --- lignes régulières ---
            solde = amount_total - montant_acomptes
            worksheet.write(line_number, 0, date_due.split(' ')[0] if date_due else '', styles['text_border'])
            worksheet.write(line_number, 1, move.name, styles['text_border'])
            worksheet.write(line_number, 2, move.date.split(' ')[0], styles['text_border'])
            worksheet.write(line_number, 3, move.partner_id.name, styles['text_border'])
            worksheet.write(line_number, 4, move.ref, styles['text_border'])
            worksheet.write(line_number, 5, payment_term and payment_term.name or '', styles['text_border'])
            worksheet.write(line_number, 6, amount_total - taxes, styles['number_border'])
            worksheet.write(line_number, 7, amount_total, styles['number_border'])
            worksheet.write(line_number, 8, montant_acomptes, styles['number_border'])
            worksheet.write(line_number, 9, solde, styles['number_bold_border'])
            line_number += 1

        # --- Ajout de la ligne de la dernière semaine ---
        if solde:
            worksheet.merge_range(
                line_number, 0, line_number, 5,
                u"Total sans date d'échéance" if date and not day else u"Total de la date d'échéance " + date,
                styles['text_total_border'])
            for col in range(6, 10):
                worksheet.write(
                    line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col),
                    styles['number_total_border'])
            total.append(line_number)
            line_number += 1

        # --- Ligne de récap total ---
        if solde and total:
            worksheet.merge_range(line_number, 0, line_number, 5, 'Total', styles['text_title_border'])
            for col in range(6, 10):
                val = '=%s' % ('+'.join([xl_rowcol_to_cell(x, col) for x in total]))
                worksheet.write(line_number, col, val, styles['number_title_border'])

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        return base64.b64encode(data)

    @api.multi
    def _create_stats_excel(self):
        # --- Ouverture du workbook ---
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})

        # --- Couleur de police ---
        styles = self._get_styles_excel(workbook)

        n_start = self.period_n.date_start if self.type_filtre_date == 'period' else self.debut_n
        n_end = self.period_n.date_end if self.type_filtre_date == 'period' else self.fin_n
        n1_start = self.period_n1.date_start if self.type_filtre_date == 'period' else self.debut_n1
        n1_end = self.period_n1.date_end if self.type_filtre_date == 'period' else self.fin_n1
        #  Création des domaines
        sale_order_domain = [
            ('state', '!=', 'draft'),
            '|',
            '&', ('confirmation_date', '>=', n_start), ('confirmation_date', '<=', n_end),
            '&', ('confirmation_date', '>=', n1_start), ('confirmation_date', '<=', n1_end)]

        account_invoice_domain = [
            ('state', 'in', ['open', 'paid']), ('type', 'in', ['out_invoice', 'out_refund']),
            '|',
            '&', ('date_invoice', '>=', n_start), ('date_invoice', '<=', n_end),
            '&', ('date_invoice', '>=', n1_start), ('date_invoice', '<=', n1_end)]

        if self.company_ids:
            sale_order_domain += [('company_id', 'in', self.company_ids._ids)]
            account_invoice_domain += [('company_id', 'in', self.company_ids._ids)]

        if self.partner_ids and self.filtre_client:
            sale_order_domain += [('partner_id', 'in', self.partner_ids._ids)]
            account_invoice_domain += [('partner_id', 'in', self.partner_ids._ids)]

        if self.etiquette_ids and self.filtre_client:
            sale_order_domain += [('partner_id.category_id', 'in', self.etiquette_ids._ids)]
            account_invoice_domain += [('partner_id.category_id', 'in', self.etiquette_ids._ids)]

        line_domain = []
        if self.product_ids and self.filtre_article:
            line_domain += [('product_id', 'in', self.product_ids._ids)]

        if self.category_ids and self.filtre_article:
            line_domain += [('product_id.categ_id', 'child_of', self.category_ids._ids)]

        if self.brand_ids and self.filtre_article:
            line_domain += [('product_id.brand_id', 'in', self.brand_ids._ids)]

        orders = self.env['sale.order'].search(sale_order_domain)
        invoices = self.env['account.invoice'].search(account_invoice_domain)
        order_line_domain = line_domain + [('order_id', 'in', orders._ids)]
        invoice_line_domain = line_domain + [('invoice_id', 'in', invoices._ids)]
        order_lines = self.env['sale.order.line'].search(order_line_domain).sorted('order_partner_id')
        invoice_lines = self.env['account.invoice.line'].search(invoice_line_domain).sorted('partner_id')

        # must be stats_partner = {client: {produit: {period_n:{qty: x, prix:y}, period_n1:{qty: x, prix:y}}, qté: 'x'}}
        stats_partner = {}
        # must be stats_categ = {categ: {client: {period_n:{qty: x, prix:y}, period_n1:{qty: x, prix:y}}, qté: 'x'}}
        stats_categ = {}
        # must be stats_brand = {marque: {client: {period_n:{qty: x, prix:y}, period_n1:{qty: x, prix:y}}, qté: 'x'}}
        stats_brand = {}
        # Le dummy est prévu pour pouvoir le trier de la même façon que les autres dictionnaires
        recap_product = {"dummy": {}}

        # Récupération des valeurs dans les dictionnaires
        for lines in [order_lines, invoice_lines]:
            model = lines._name
            for line in lines :
                if model == 'sale.order.line':
                    if line.product_uom_qty == 0:
                        continue

                    partner = line.order_partner_id.commercial_partner_id

                    if partner not in stats_partner:
                        stats_partner[partner] = {'oqté': 0, 'iqté': 0}
                    partners_and_products = stats_partner[partner]
                    if line.product_id not in partners_and_products:
                        partners_and_products[line.product_id] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    partners_and_products = partners_and_products[line.product_id]

                    if line.product_id not in recap_product["dummy"]:
                        recap_product["dummy"][line.product_id] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    rec_pr = recap_product["dummy"][line.product_id]

                    if line.product_id.categ_id not in stats_categ:
                        stats_categ[line.product_id.categ_id] = {'oqté': 0, 'iqté': 0}
                    categs_and_partners = stats_categ[line.product_id.categ_id]
                    categ = line.product_id.categ_id
                    if partner not in categs_and_partners:
                        categs_and_partners[partner] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    categs_and_partners = categs_and_partners[partner]

                    if line.product_id.brand_id not in stats_brand:
                        stats_brand[line.product_id.brand_id] = {
                            'oqté': 0, 'oca': 0, 'oqté1': 0, 'oca1': 0, 'iqté': 0, 'ica': 0, 'iqté1': 0, 'ica1': 0,
                        }
                    brands_and_partners = stats_brand[line.product_id.brand_id]
                    brand = line.product_id.brand_id
                    if partner not in brands_and_partners:
                        brands_and_partners[partner] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    brands_and_partners = brands_and_partners[partner]

                    if line.order_id.confirmation_date >= n_start and line.order_id.confirmation_date <= n_end:
                        stats_partner[partner]['oqté'] += line.product_uom_qty
                        stats_categ[categ]['oqté'] += line.product_uom_qty
                        stats_brand[brand]['oqté'] += line.product_uom_qty
                        stats_brand[brand]['oca'] += line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        partners_and_products[n_start]['oqté'] += line.product_uom_qty
                        partners_and_products[n_start]['oprix'] +=\
                            line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        categs_and_partners[n_start]['oqté'] += line.product_uom_qty
                        categs_and_partners[n_start]['oprix'] +=\
                            line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        brands_and_partners[n_start]['oqté'] += line.product_uom_qty
                        brands_and_partners[n_start]['oprix'] +=\
                            line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        rec_pr[n_start]['oqté'] += line.product_uom_qty
                        rec_pr[n_start]['oprix'] += line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                    else:
                        stats_brand[brand]['oqté1'] += line.product_uom_qty
                        stats_brand[brand]['oca1'] += line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        partners_and_products[n1_start]['oqté'] += line.product_uom_qty
                        partners_and_products[n1_start]['oprix'] +=\
                            line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        categs_and_partners[n1_start]['oqté'] += line.product_uom_qty
                        categs_and_partners[n1_start]['oprix'] +=\
                            line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        brands_and_partners[n1_start]['oqté'] += line.product_uom_qty
                        brands_and_partners[n1_start]['oprix'] +=\
                            line.price_unit * line.product_uom_qty * (1 - line.discount / 100)
                        rec_pr[n1_start]['oqté'] += line.product_uom_qty
                        rec_pr[n1_start]['oprix'] += line.price_unit * line.product_uom_qty * (1 - line.discount / 100)

                else:
                    if line.quantity == 0:
                        continue

                    partner = line.partner_id.commercial_partner_id

                    if partner not in stats_partner:
                        stats_partner[partner] = {'oqté': 0, 'iqté': 0}
                    partners_and_products = stats_partner[partner]
                    if line.product_id not in partners_and_products:
                        partners_and_products[line.product_id] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    partners_and_products = partners_and_products[line.product_id]

                    if line.product_id not in recap_product["dummy"]:
                        recap_product["dummy"][line.product_id] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    rec_pr = recap_product["dummy"][line.product_id]

                    if line.product_id.categ_id not in stats_categ:
                        stats_categ[line.product_id.categ_id] = {'oqté': 0, 'iqté': 0}
                    categs_and_partners = stats_categ[line.product_id.categ_id]
                    categ = line.product_id.categ_id
                    if partner not in categs_and_partners:
                        categs_and_partners[partner] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    categs_and_partners = categs_and_partners[partner]

                    if line.product_id.brand_id not in stats_brand:
                        stats_brand[line.product_id.brand_id] = {
                            'oqté': 0, 'oca': 0, 'oqté1': 0, 'oca1': 0, 'iqté': 0, 'ica': 0, 'iqté1': 0, 'ica1': 0}
                    brands_and_partners = stats_brand[line.product_id.brand_id]
                    brand = line.product_id.brand_id
                    if partner not in brands_and_partners:
                        brands_and_partners[partner] = {
                            n_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                            n1_start: {'oqté': 0, 'oprix': 0, 'iqté': 0, 'iprix': 0},
                        }
                    brands_and_partners = brands_and_partners[partner]

                    if line.invoice_id.date_invoice >= n_start and line.invoice_id.date_invoice <= n_end:
                        sign = 1 if line.invoice_id.type == 'out_invoice' else -1
                        stats_partner[partner]['iqté'] += line.quantity * sign
                        stats_categ[categ]['iqté'] += line.quantity * sign
                        stats_brand[brand]['iqté'] += line.quantity * sign
                        stats_brand[brand]['ica'] += line.price_subtotal_signed
                        partners_and_products[n_start]['iqté'] += line.quantity * sign
                        partners_and_products[n_start]['iprix'] += line.price_subtotal_signed
                        categs_and_partners[n_start]['iqté'] += line.quantity * sign
                        categs_and_partners[n_start]['iprix'] += line.price_subtotal_signed
                        brands_and_partners[n_start]['iqté'] += line.quantity * sign
                        brands_and_partners[n_start]['iprix'] += line.price_subtotal_signed
                        rec_pr[n_start]['iqté'] += line.quantity * sign
                        rec_pr[n_start]['iprix'] += line.price_subtotal_signed
                    else:
                        sign = 1 if line.invoice_id.type == 'out_invoice' else -1
                        stats_brand[brand]['iqté1'] += line.quantity * sign
                        stats_brand[brand]['ica1'] += line.price_subtotal_signed
                        partners_and_products[n1_start]['iqté'] += line.quantity * sign
                        partners_and_products[n1_start]['iprix'] += line.price_subtotal_signed
                        categs_and_partners[n1_start]['iqté'] += line.quantity * sign
                        categs_and_partners[n1_start]['iprix'] += line.price_subtotal_signed
                        brands_and_partners[n1_start]['iqté'] += line.quantity * sign
                        brands_and_partners[n1_start]['iprix'] += line.price_subtotal_signed
                        rec_pr[n1_start]['iqté'] += line.quantity * sign
                        rec_pr[n1_start]['iprix'] += line.price_subtotal_signed

        # un premier tri qui permet d'avoir les tableaux dans l'ordre décroissant
        sorted_partner = sorted(stats_partner.items(), key=lambda data: data[1]['oqté'], reverse=True)
        sorted_categ = sorted(stats_categ.items(), key=lambda data: data[1]['oqté'], reverse=True)
        sorted_brand = sorted(stats_brand.items(), key=lambda data: data[1]['oqté'], reverse=True)
        sorted_product = sorted(recap_product.items(), key=lambda data: data[1])

        stats = []
        if self.stats_partner:
            stats.append(('product', sorted_product, 'Statistique de ventes par produit'))
            stats.append(('partner', sorted_partner, 'Statistiques de ventes par client'))
        if self.stats_product:
            stats.append(('categ', sorted_categ, u'Statistiques de ventes par catégorie de produit'))
        if self.stats_brand:
            stats.append(('categ', sorted_brand, u'statistiques de ventes par marques'))

        for page, values, name in stats:
            # --- Création de la page ---
            worksheet = workbook.add_worksheet(name)
            worksheet.set_paper(9)  # Format d'impression A4
            worksheet.set_landscape()  # Format d'impression paysage
            worksheet.set_margins(left=0.35, right=0.35, top=0.2, bottom=0.2)

            # --- Initialisation des colonnes ---
            worksheet.set_column(0, 0, 35)      # Largeur colonne 'nom du client/produit'
            worksheet.set_column(1, 1, 10)      # Largeur colonne 'Période N Qté'
            worksheet.set_column(2, 2, 10)      # Largeur colonne 'Période N-1 Qté'
            worksheet.set_column(3, 3, 12)      # Largeur colonne 'Evo % Qté'
            worksheet.set_column(4, 4, 16)      # Largeur colonne 'Période N CA'
            worksheet.set_column(5, 5, 16)      # Largeur colonne 'Période N-1 CA'
            worksheet.set_column(6, 6, 12)      # Largeur colonne 'Evo % CA
            worksheet.set_column(7, 4, 16)      # Largeur colonne 'Période N Facturé'
            worksheet.set_column(8, 5, 16)      # Largeur colonne 'Période N-1 Facturé'
            worksheet.set_column(9, 6, 12)      # Largeur colonne 'Evo % Facturé'
            worksheet.set_row(0, 20)
            worksheet.set_row(1, 20)

            worksheet.merge_range(0, 0, 0, 1, 'Nom du fichier', styles['text_title_ita_border'])
            worksheet.merge_range(0, 2, 0, 5, u'Date de création', styles['text_title_ita_border'])
            worksheet.merge_range(0, 6, 0, 8, u'Société(s)' , styles['text_title_ita_border'])
            worksheet.merge_range(
                0, 9, 0, 11, u'Périodes : N / N-1' if self.type_filtre_date == 'period' else 'Dates',
                styles['text_title_ita_border'])
            worksheet.merge_range(1, 0, 1, 1, name, styles['text_title_border'])
            worksheet.merge_range(1, 2, 1, 5, self.date, styles['text_title_border'])
            worksheet.merge_range(
                1, 6, 1, 8, ", ".join(self.company_ids.mapped('name')), styles['text_title_border_wrap'])
            if self.type_filtre_date == 'period':
                worksheet.merge_range(
                    1, 9, 1, 11, self.period_n.name + ' / ' + self.period_n1.name, styles['text_title_border_wrap'])
            else:
                worksheet.merge_range(
                    1, 9, 1, 11, self.debut_n + ' - ' + self.fin_n + '\n' + self.debut_n1 + ' - ' + self.fin_n1,
                    styles['text_title_border_wrap'])

            line_number = 3

            # Ajout d'un récap pour les marques
            if page == 'brand':
                worksheet.merge_range(
                    line_number, 0, line_number + 1, 0, u"Récap. marques", styles['text_title_border_red'])
                worksheet.merge_range(
                    line_number, 1, line_number, 3,  u'Qté - Commandes en cours', styles['text_title_border'])
                worksheet.merge_range(line_number, 4, line_number, 6, u'CA commandé', styles['text_title_border'])
                worksheet.merge_range(line_number, 7, line_number, 9, u'CA facturé', styles['text_title_border'])
                line_number += 1
                worksheet.write(line_number, 1, 'N', styles['text_title_border'])
                worksheet.write(line_number, 2, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 3, 'Evo %', styles['text_title_border'])
                worksheet.write(line_number, 4, 'N', styles['text_title_border'])
                worksheet.write(line_number, 5, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 6, 'Evo %', styles['text_title_border'])
                worksheet.write(line_number, 7, 'N', styles['text_title_border'])
                worksheet.write(line_number, 8, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 9, 'Evo %', styles['text_title_border'])
                line_number += 1
                line_keep = line_number

                for obj, valeurs in values:
                    qty_n = valeurs['oqté']
                    qty_n1 = valeurs['oqté1']
                    price_n = valeurs['oca']
                    price_n1 = valeurs['oca1']
                    fprice_n = valeurs['ica']
                    fprice_n1 = valeurs['ica1']
                    worksheet.write(line_number, 0, obj.name, styles['text_border_left'])
                    worksheet.write(line_number, 1, qty_n, styles['number_border'])
                    worksheet.write(line_number, 2, qty_n1, styles['number_border'])
                    worksheet.write(
                        line_number, 3,
                        '=(%s / %s - 1)' % (
                            xl_rowcol_to_cell(line_number, 1),
                            xl_rowcol_to_cell(line_number, 2)) if qty_n1 else 1,
                        styles['number_border_percent'])
                    worksheet.write(line_number, 4, price_n, styles['number_border'])
                    worksheet.write(line_number, 5, price_n1, styles['number_border'])
                    worksheet.write(
                        line_number, 6,
                        '=(%s / %s - 1)' % (
                            xl_rowcol_to_cell(line_number, 4),
                            xl_rowcol_to_cell(line_number, 5)) if price_n1 else 1,
                        styles['number_border_percent'])
                    worksheet.write(line_number, 7, fprice_n, styles['number_border'])
                    worksheet.write(line_number, 8, fprice_n1, styles['number_border'])
                    worksheet.write(
                        line_number, 9,
                        '=(%s / %s - 1)' % (
                            xl_rowcol_to_cell(line_number, 7),
                            xl_rowcol_to_cell(line_number, 8)) if fprice_n1 else 1,
                        styles['number_border_percent'])
                    line_number += 1

                worksheet.write(line_number, 0, 'TOTAL', styles['text_title_border_blue_left'])
                for column in range(1, 10):
                    if column in (3, 6, 9):
                        worksheet.write(
                            line_number, column,
                            '=IF(%s>0,(%s / %s - 1),1)' % (
                                xl_rowcol_to_cell(line_number, column-1),
                                xl_rowcol_to_cell(line_number, column-2),
                                xl_rowcol_to_cell(line_number, column-1)),
                            styles['number_title_border_blue_percent'])
                    else:
                        worksheet.write(
                            line_number, column,
                            '=SUM(%s:%s)' % (
                                xl_rowcol_to_cell(line_keep, column),
                                xl_rowcol_to_cell(line_number - 1, column)),
                            styles['number_title_border_blue'])
                line_number += 2
                # fin du récap des marques

            for obj, valeurs in values:
                if valeurs.get('oqté', None) is not None:
                    # On n'a plus besoin de la quantité dans le dictionnaire
                    # On l'enlève pour pouvoir trier correctement
                    del valeurs['oqté']
                if valeurs.get('iqté', None) is not None:
                    del valeurs['iqté']
                if 'oqté1' in valeurs:
                    # Si ils sont présents on les enlève
                    del valeurs['oqté1']
                    del valeurs['oca']
                    del valeurs['oca1']
                    del valeurs['iqté1']
                    del valeurs['ica']
                    del valeurs['ica1']
                worksheet.merge_range(
                    line_number, 0, line_number + 1, 0, obj.name if page != 'product' else u'Vente produits',
                    styles['text_title_border_red'])
                worksheet.merge_range(
                    line_number, 1, line_number, 3,  u'Qté - Commandes en cours', styles['text_title_border'])
                worksheet.merge_range(line_number, 4, line_number, 6, u'CA commandé', styles['text_title_border'])
                worksheet.merge_range(line_number, 7, line_number, 9, u'CA facturé', styles['text_title_border'])
                line_number += 1
                worksheet.write(line_number, 1, 'N', styles['text_title_border'])
                worksheet.write(line_number, 2, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 3, 'Evo %', styles['text_title_border'])
                worksheet.write(line_number, 4, 'N', styles['text_title_border'])
                worksheet.write(line_number, 5, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 6, 'Evo %', styles['text_title_border'])
                worksheet.write(line_number, 7, 'N', styles['text_title_border'])
                worksheet.write(line_number, 8, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 9, 'Evo %', styles['text_title_border'])
                line_number += 1
                line_keep = line_number
                # Tri secondaire par period_n1 croissant
                valeurs = sorted(valeurs.items(), key=lambda data: data[1][n1_start]['oqté'])
                # Tri principal par period_n décroissant
                valeurs = sorted(valeurs, key=lambda data: data[1][n_start]['oqté'], reverse=True)
                for entry, data in valeurs:
                    qty_n = data[n_start]['oqté']
                    qty_n1 = data[n1_start]['oqté']
                    price_n = data[n_start]['oprix']
                    price_n1 = data[n1_start]['oprix']
                    fprice_n = data[n_start]['iprix']
                    fprice_n1 = data[n1_start]['iprix']
                    worksheet.write(line_number, 0, entry.name, styles['text_border_left'])
                    worksheet.write(line_number, 1, qty_n, styles['number_border'])
                    worksheet.write(line_number, 2, qty_n1, styles['number_border'])
                    worksheet.write(
                        line_number, 3,
                        '=(%s / %s - 1)' % (
                            xl_rowcol_to_cell(line_number, 1),
                            xl_rowcol_to_cell(line_number, 2)) if qty_n1 else 1,
                        styles['number_border_percent'])
                    worksheet.write(line_number, 4, price_n, styles['number_border'])
                    worksheet.write(line_number, 5, price_n1, styles['number_border'])
                    worksheet.write(
                        line_number, 6,
                        '=(%s / %s - 1)' % (
                            xl_rowcol_to_cell(line_number, 4),
                            xl_rowcol_to_cell(line_number, 5)) if price_n1 else 1,
                        styles['number_border_percent'])
                    worksheet.write(line_number, 7, fprice_n, styles['number_border'])
                    worksheet.write(line_number, 8, fprice_n1, styles['number_border'])
                    worksheet.write(
                        line_number, 9,
                        '=(%s / %s - 1)' % (
                            xl_rowcol_to_cell(line_number, 7),
                            xl_rowcol_to_cell(line_number, 8)) if fprice_n1 else 1,
                        styles['number_border_percent'])
                    line_number += 1
                worksheet.write(line_number, 0, 'TOTAL', styles['text_title_border_blue_left'])
                for column in range(1, 10):
                    if column in (3, 6, 9):
                        worksheet.write(
                            line_number, column,
                            '=IF(%s>0,(%s / %s - 1),1)' % (
                                xl_rowcol_to_cell(line_number, column-1),
                                xl_rowcol_to_cell(line_number, column-2),
                                xl_rowcol_to_cell(line_number, column-1)),
                            styles['number_title_border_blue_percent'])
                    else:
                        worksheet.write(
                            line_number, column,
                            '=SUM(%s:%s)' % (
                                xl_rowcol_to_cell(line_keep, column),
                                xl_rowcol_to_cell(line_number - 1, column)),
                            styles['number_title_border_blue'])
                line_number += 2

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        return base64.b64encode(data)

    @api.multi
    def _create_encaissements_excel(self):
        # --- Ouverture du workbook ---
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})

        # --- Couleur de police ---
        styles = self._get_styles_excel(workbook)

        # --- Création de la page ---
        worksheet = workbook.add_worksheet(self.file_name.split('.')[0])
        worksheet.set_paper(9)  # Format d'impression A4
        worksheet.set_landscape()  # Format d'impression paysage
        worksheet.set_margins(left=0.35, right=0.35, top=0.2, bottom=0.2)

        # --- Initialisation des colonnes ---
        worksheet.set_column(0, 0, 12)  # Largeur colonne 'Date'
        worksheet.set_column(1, 1, 20)  # Largeur colonne 'Partenaire'
        worksheet.set_column(2, 2, 20)  # Largeur colonne 'Paiements'
        worksheet.set_column(3, 3, 16)  # Largeur colonne 'Factures'
        worksheet.set_column(4, 4, 10)  # Largeur colonne 'Montant'
        worksheet.set_column(5, 5, 10)  # Largeur colonne 'taxe 1'
        worksheet.set_column(6, 6, 10)  # Largeur colonne 'taxe 2'
        worksheet.set_column(7, 7, 10)  # Largeur colonne 'taxe 3'
        worksheet.set_column(8, 8, 10)  # Largeur colonne 'taxe 4'
        worksheet.set_column(9, 9, 10)  # Largeur colonne 'taxe 5'
        worksheet.set_column(10, 10, 10)  # Largeur colonne 'taxe 6'

        # --- Entête ---
        worksheet.merge_range(0, 0, 0, 2, 'Nom du fichier', styles['text_title_ita_border'])
        worksheet.merge_range(0, 3, 0, 5, u'Date de création', styles['text_title_ita_border'])
        worksheet.merge_range(0, 6, 0, 8, u'Société(s)', styles['text_title_ita_border'])
        worksheet.merge_range(1, 0, 1, 2, self.file_name.split('.')[0], styles['text_title_border'])
        worksheet.merge_range(1, 3, 1, 5, self.date, styles['text_title_border'])
        worksheet.merge_range(1, 6, 1, 8, ", ".join(self.company_ids.mapped('name')), styles['text_title_border_wrap'])

        # --- Ajout des lignes ---
        line_number = 3
        payment_obj = self.env['account.payment']
        tax_obj = self.env['account.tax']
        domain = [('partner_type', '=', 'customer')]
        if self.type_filtre_date == 'period':
            domain += [('payment_date', '>=', self.period_n.date_start), ('payment_date', '<=', self.period_n.date_end)]
        else:
            domain += [('payment_date', '>=', self.debut_n), ('payment_date', '<=', self.fin_n)]
        companies = self.company_ids or self.env['res.company'].search([])
        if self.company_ids:
            domain += [('company_id', 'in', self.company_ids._ids)]
        payments = payment_obj.search(domain, order='payment_date')
        # Les comptes de taxe sont triés par ordre de montant
        taxes = tax_obj.search([('type_tax_use', '=', 'sale')], order='amount')
        sorted_accounts = taxes.mapped('account_id')
        correspondance = {}
        for tax in taxes:
            if tax.account_id not in correspondance:
                correspondance[tax.account_id] = tax.mapped('account_ids').mapped('account_dest_id')
            else:
                correspondance[tax.account_id] |= tax.mapped('account_ids').mapped('account_dest_id')

        display = {}
        for company in companies:
            # Vérification par société
            payment_filtered = payments.filtered(lambda p: p.company_id == company)
            display[company] = {'payments': {}, 'tax_account_used': {}, 'undefined_payments': [], 'taxes': []}
            display_company = display[company]
            payments_dict = display_company['payments']
            tax_account_used_dict = display_company['tax_account_used']
            undefined_payments_list = display_company['undefined_payments']
            tax_accounts = self.env['account.account']
            tax_column = 5
            tax_column_increment = 3  # 3 colonnes par taxes : HT, TAXE, TTC

            for payment in payment_filtered:
                affectations = []
                aml = payment.move_line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable')
                invoice_move_lines = aml.mapped('matched_credit_ids').mapped('credit_move_id')
                invoice_move_lines |= aml.mapped('matched_debit_ids').mapped('debit_move_id')
                credit = sum(aml.mapped('credit'))
                reconciles = invoice_move_lines.mapped('matched_credit_ids')\
                                               .filtered(lambda r: r.credit_move_id.id in aml._ids)
                total = 0.0
                for reconcile in reconciles:
                    affectations.append((reconcile.debit_move_id.move_id, reconcile.amount))
                    total += reconcile.amount

                # Vérification que le montant total lettré est égal au montant du paiement
                if float_compare(total, credit, 2) == 0:
                    # Calcul du montant affecté aux différents comptes de taxes
                    for invoice_move, amount in affectations:
                        invoice_partner_lines = invoice_move.line_ids.filtered(
                            lambda l: l.account_id.internal_type in ('receivable', 'payable'))
                        invoice_partner_amount = \
                            sum(invoice_partner_lines.mapped('debit')) - sum(invoice_partner_lines.mapped('credit'))
                        percent = amount / invoice_partner_amount
                        payment_dict = payments_dict.setdefault(payment, {})
                        tax_move_lines = invoice_move.line_ids.filtered(lambda l: l.account_id in sorted_accounts)
                        for tax_move_line in tax_move_lines:
                            account = tax_move_line.account_id
                            tax_accounts |= account
                            if account not in payment_dict:
                                payment_dict[account] = {"ht": 0.0, "taxe": 0.0}
                            payment_dict[account]["taxe"] -= tax_move_line.balance * percent
                            corresponding_ht_lines = invoice_move.line_ids.filtered(
                                lambda ml: ml.account_id.id in correspondance[account]._ids)
                            payment_dict[account]["ht"] -= percent * sum(corresponding_ht_lines.mapped('balance'))
                else:
                    # On conserve les paiements non intégralement lettrés pour les signaler a l'utilisateur
                    undefined_payments_list.append(payment)
            for account in sorted_accounts & tax_accounts:
                tax_account_used_dict[account] = tax_column
                tax_column += tax_column_increment

        for company, display_company in display.iteritems():
            # Affichage par société
            payments_sorted = sorted(display_company['payments'].iteritems(), key=lambda x: x[0].payment_date)
            tax_account_used_dict = display_company['tax_account_used']
            undefined_payments_list = display_company['undefined_payments']
            line_number += 1
            worksheet.merge_range(line_number, 0, line_number, 4, company.name, styles['text_title_border_red'])
            line_number += 1

            worksheet.write(line_number, 0, "Date", styles['text_title_border'])
            worksheet.write(line_number, 1, "Partenaire", styles['text_title_border'])
            worksheet.write(line_number, 2, "Paiements", styles['text_title_border'])
            worksheet.write(line_number, 3, "Factures", styles['text_title_border'])
            worksheet.write(line_number, 4, "Montant", styles['text_title_border'])

            # Création des colonnes de taxes
            for tax in tax_account_used_dict.keys():
                worksheet.merge_range(
                    line_number-1, tax_account_used_dict[tax],
                    line_number-1, tax_account_used_dict[tax]+2,
                    "%s-%s" % (tax.code, tax.name), styles['text_title_ita_border'])
                worksheet.write(
                    line_number, tax_account_used_dict[tax], "HT", styles['text_title_border'])
                worksheet.write(
                    line_number, tax_account_used_dict[tax]+1, "TVA",
                    styles['text_title_border_yellow'])
                worksheet.write(
                    line_number, tax_account_used_dict[tax]+2, "TTC", styles['text_title_border'])
                if any([col_num > 8 for col_num in xrange(tax_account_used_dict[tax], tax_account_used_dict[tax]+3)]):
                    worksheet.set_column(tax_account_used_dict[tax], tax_account_used_dict[tax], 10)
                    worksheet.set_column(tax_account_used_dict[tax], tax_account_used_dict[tax]+1, 10)
                    worksheet.set_column(tax_account_used_dict[tax], tax_account_used_dict[tax]+2, 10)
            line_number += 1
            line_keep = line_number
            # Ajout des paiements et des montants par compte
            for payment, tax_dict in payments_sorted:
                worksheet.write(line_number, 0, "%s" % payment.payment_date, styles['text_title_border'])
                worksheet.write(line_number, 1, "%s" % payment.partner_id.name, styles['text_title_border'])
                worksheet.write(line_number, 2, "%s" % payment.name, styles['text_title_border'])
                invoices = payment.invoice_ids.mapped('move_name')
                worksheet.write(
                    line_number, 3, "%s" % invoices and ", ".join(invoices) or "", styles['text_title_border'])
                worksheet.write(line_number, 4, payment.amount, styles['number_title_border'])
                for tax, column in tax_account_used_dict.iteritems():
                    worksheet.write(
                        line_number, column, tax_dict[tax]["ht"] if tax in tax_dict else "", styles['number_border'])
                    worksheet.write(
                        line_number, column+1, tax_dict[tax]["taxe"] if tax in tax_dict else "",
                        styles['number_border_yellow'])
                    worksheet.write(
                        line_number, column+2,
                        '=SUM(%s:%s)' % (
                            xl_rowcol_to_cell(line_number, column),
                            xl_rowcol_to_cell(line_number, column+1)),
                        styles['number_border'])
                line_number += 1

            # Ligne du total
            worksheet.write(line_number, 0, "Total", styles['text_title_border'])
            worksheet.write(line_number, 1, "", styles['text_title_border'])
            worksheet.write(line_number, 2, "", styles['text_title_border'])
            worksheet.write(line_number, 3, "", styles['text_title_border'])
            worksheet.write(line_number, 4, "", styles['text_title_border'])
            for tax in tax_account_used_dict.keys():
                tax_column = tax_account_used_dict[tax]
                worksheet.write(
                    line_number, tax_column,
                    '=SUM(%s:%s)' % (
                        xl_rowcol_to_cell(line_keep, tax_column),
                        xl_rowcol_to_cell(line_number - 1, tax_column)),
                    styles['number_title_border'])
                worksheet.write(
                    line_number, tax_column+1,
                    '=SUM(%s:%s)' % (
                        xl_rowcol_to_cell(line_keep, tax_column+1),
                        xl_rowcol_to_cell(line_number - 1, tax_column+1)),
                    styles['number_title_border_yellow'])
                worksheet.write(
                    line_number, tax_column+2,
                    '=SUM(%s:%s)' % (
                        xl_rowcol_to_cell(line_keep, tax_column+2),
                        xl_rowcol_to_cell(line_number - 1, tax_column+2)),
                    styles['number_title_border'])
            line_number += 2

            # Si des paiements sont présent dans la liste, on les affiches à la fin
            if undefined_payments_list:
                worksheet.merge_range(
                    line_number, 0, line_number, 4, u"Les paiements suivants ne sont pas complètement lettrés",
                    styles['text_title_ita_border'])
                line_number += 1
                while undefined_payments_list:
                    payment = undefined_payments_list.pop()
                    worksheet.write(line_number, 0, "%s" % payment.name, styles['text_title_border'])
                    worksheet.write(line_number, 1, "%s" % payment.partner_id.name, styles['text_title_border'])
                    worksheet.write(line_number, 2, "%s" % payment.payment_date, styles['text_title_border'])
                    worksheet.write(line_number, 3, "%s" % "", styles['text_title_border'])
                    worksheet.write(line_number, 4, "%s" % payment.amount, styles['text_title_border'])
                    line_number += 1
                line_number += 1

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        return base64.b64encode(data)

    FUNDICT = {
        'encours': '_create_encours_excel',
        'echeancier': '_create_echeancier_excel',
        'stats': '_create_stats_excel',
        'encaissement': '_create_encaissements_excel',
        'autre': '_dummy_function'
    }

    # Grâce au return do_nothing
    # on peut appuyer sur le bouton et ne pas avoir à renvoyer la vue
    # pour mettre à jour les informations
    @api.multi
    def button_print(self):
        file_name = {
            'encours': 'Encours des commandes de vente.xlsx',
            'echeancier': u'Échéancier des règlements fournisseurs.xlsx',
            'stats': "Statistiques de ventes.xlsx",
            'encaissement': 'TVA sur encaissement.xlsx',
            'autre': 'Autre.xlsx'
        }
        self.file_name = file_name[self.report_model]
        self.file = getattr(self, self.FUNDICT[self.report_model])()
        return {"type": "ir.actions.do_nothing"}
