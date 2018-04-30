# -*- coding: utf-8 -*-

import base64
import datetime
from odoo import models, fields, api
from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range


class OFRapportOpenflamWizard(models.TransientModel):
    _name = 'of.rapport.openflam.wizard'
    _description = 'Rapport Openflam'

    file_name = fields.Char('Nom du fichier', size=64, default=u'Encours des commandes de vente.xlsx')
    file = fields.Binary('file')
    company_ids = fields.Many2many('res.company', string=u'Sociétés')
    date = fields.Date(u'Date de création', default=datetime.datetime.now().strftime("%Y-%m-%d"))
    report_model = fields.Selection([('encours', u'État des encours de commandes de vente'),
                                     ('echeancier', u'Échéancier des règlements fournisseurs'),
                                     ('autre', 'Autre')],
                                     string=u"Modèle de rapport", required=True, default='encours')

    @api.multi
    def _action_return(self):
        action = self.env.ref('of_sale_report.action_of_rapport_openflam').read()[0]
        action['views'] = [(self.env.ref('of_sale_report.of_rapport_openflam_view_form').id, 'form')]
        action['res_id'] = self.ids[0]
        return action

    @api.multi
    def _dummy_function(self):
        self.file = False
        return self._action_return()

    def _get_styles_excel(self, workbook):
        color_light_gray = '#C0C0C0'
        color_lighter_gray = '#D9D9D9'
        #color_light_blue = '#4040A0'

        style_text_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
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
            'bg_color' : color_light_gray,
        })

        style_text_title_border_wrap = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'text_wrap': True,
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_light_gray,
        })

        style_text_title_ita_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'italic': True,
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_light_gray,
        })

        style_text_total_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'left',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_lighter_gray,
        })

        style_number_border = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00',
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
            'bg_color' : color_light_gray,
            'num_format': '#,##0.00',
        })

        style_number_total_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_lighter_gray,
            'num_format': '#,##0.00',
        })

        return {
        'text_border': style_text_border,
        'text_bold_border': style_text_bold_border,
        'text_title_border': style_text_title_border,
        'text_title_ita_border': style_text_title_ita_border,
        'text_title_border_wrap': style_text_title_border_wrap,
        'text_total_border': style_text_total_border,
        'number_border': style_number_border,
        'number_bold_border': style_number_bold_border,
        'number_title_border': style_number_title_border,
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
        worksheet.set_column(2, 2, 16)      # Largeur colonne 'Pose prévisionelle'
        worksheet.set_column(3, 3, 20)       # Largeur colonne 'Nom client'
        worksheet.set_column(4, 4, 16)      # Largeur colonne 'Vendeur'
        worksheet.set_column(5, 5, 16)      # Largeur colonne 'Total HT'
        worksheet.set_column(6, 6, 16)      # Largeur colonne 'Total TTC'
        worksheet.set_column(7, 7, 25)       # Largeur colonne 'Accompte(s) versé(s) (total)'
        worksheet.set_column(8, 8, 20)       # Largeur colonne 'Solde'

        # --- Entête ---
        worksheet.merge_range(0, 0, 0, 2, 'Nom du fichier', styles['text_title_ita_border'])
        worksheet.merge_range(0, 3, 0, 5, u'Date de création', styles['text_title_ita_border'])
        worksheet.merge_range(0, 6, 0, 8, u'Société(s)' , styles['text_title_ita_border'])
        worksheet.merge_range(1, 0, 1, 2, self.file_name.split('.')[0], styles['text_title_border'])
        worksheet.merge_range(1, 3, 1, 5, self.date, styles['text_title_border'])
        worksheet.merge_range(1, 6, 1, 8, ", ".join(self.company_ids.mapped('name')), styles['text_title_border_wrap'])

        # --- Ajout des lignes ---
        line_number = 3
        worksheet.write(line_number, 0, 'Date CC', styles['text_title_border'])
        worksheet.write(line_number, 1, u'n° CC', styles['text_title_border'])
        worksheet.write(line_number, 2, u'Pose prévisionelle', styles['text_title_border'])
        worksheet.write(line_number, 3, 'Nom du client', styles['text_title_border'])
        worksheet.write(line_number, 4, 'Vendeur', styles['text_title_border'])
        worksheet.write(line_number, 5, 'Total HT', styles['text_title_border'])
        worksheet.write(line_number, 6, 'Total TTC', styles['text_title_border'])
        worksheet.write(line_number, 7, u'Accompte(s) versé(s) (total)', styles['text_title_border'])
        worksheet.write(line_number, 8, 'solde', styles['text_title_border'])
        line_number += 1
        solde = 0
        week, total = [], []
        orders = self.env['sale.order'].search(['&', ('state', '!=', 'draft'), ('company_id', 'in', self.company_ids._ids)]).sorted(key=lambda r: r.of_date_de_pose)
        line_keep = line_number
        date = 0
        for order in orders:
            # --- Vérification du montant des accomptes ---
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
                worksheet.merge_range(line_number, 0, line_number, 4, u'Total sans date de pose prévisionelle' if date and week and not week[-1]
                                                                    else 'Total de la semaine ' + week[-1], styles['text_total_border'])
                week.append(date)
                for col in range(5, 8):
                    worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
                worksheet.write(line_number, 8, solde, styles['number_total_border'])
                total.append(line_number)
                line_number += 1
                line_keep = line_number

            # --- lignes régulières ---
            solde += order.amount_total - montant_acomptes
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
            worksheet.merge_range(line_number, 0, line_number, 4, u'Total sans date de pose prévisionelle' if not week[-1] and not date
                                                                else 'Total de la semaine ' + week[-1], styles['text_total_border'])
            for col in range(5, 8):
                worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
            worksheet.write(line_number, 8, solde, styles['number_total_border'])
            total.append(line_number)
            line_number += 1

        # --- Ligne de récap total ---
        if solde and total:
            worksheet.merge_range(line_number, 0, line_number, 4, 'Total de toute les semaines', styles['text_title_border'])
            for col in range(5, 8):
                val = '=%s' % ('+'.join([xl_rowcol_to_cell(x, col) for x in total]))
                worksheet.write(line_number, col, val, styles['number_title_border'])
            worksheet.write(line_number, 8, solde, styles['number_title_border'])

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        self.file = base64.b64encode(data)
        return self._action_return()

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
        worksheet.set_column(3, 3, 20)       # Largeur colonne 'Fournisseur'
        worksheet.set_column(4, 4, 16)      # Largeur colonne 'Ref Fournisseur'
        worksheet.set_column(5, 5, 20)      # Largeur colonne 'conditions de règlement'
        worksheet.set_column(6, 6, 20)      # Largeur colonne 'Total HT'
        worksheet.set_column(7, 7, 20)       # Largeur colonne 'Total TTC'
        worksheet.set_column(8, 8, 25)       # Largeur colonne 'Acompte(s) versé(s)'
        worksheet.set_column(9, 9, 25)       # Largeur colonne 'Solde'

        # --- Entête ---
        worksheet.merge_range(0, 0, 0, 2, 'Nom du fichier', styles['text_title_ita_border'])
        worksheet.merge_range(0, 3, 0, 5, u'Date de création', styles['text_title_ita_border'])
        worksheet.merge_range(0, 6, 0, 8, u'Société(s)' , styles['text_title_ita_border'])
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
        worksheet.write(line_number, 8, u'Accompte(s) versé(s) (total)', styles['text_title_border'])
        worksheet.write(line_number, 9, 'solde', styles['text_title_border'])
        line_number += 1
        solde = 0
        day, total = [], []
        invoices = self.env['account.invoice'].search(['&', ('type', '=', 'in_invoice'), ('company_id', 'in', self.company_ids._ids)]).sorted(key=lambda r: r.date_due)
        line_keep = line_number
        for invoice in invoices:
            # --- Vérification du montant des accomptes ---
            payments = self.env['account.payment'].search([('communication', '=', invoice.reference)])
            montant_acomptes = sum(payment.amount for payment in payments)
            if montant_acomptes >= invoice.amount_total:
                continue

            # --- Ajout des lignes total de la semaine ---
            date = invoice.date_due and fields.Datetime.from_string(invoice.date_due).strftime("%Y-%m-%d") or ''
            if not day:
                day.append(date)
            if solde and date not in day:
                worksheet.merge_range(line_number, 0, line_number, 5, u"Total sans date d'échéance" if date and not day[-1]
                                                                    else u"Total de la date d'échéance " + day[-1], styles['text_total_border'])
                day.append(date)
                for col in range(6, 9):
                    worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
                worksheet.write(line_number, 9, solde, styles['number_total_border'])
                total.append(line_number)
                line_number += 1
                line_keep = line_number

            # --- lignes régulières ---
            solde += invoice.amount_total - montant_acomptes
            worksheet.write(line_number, 0, invoice.date_due.split(' ')[0] if invoice.date_due else '', styles['text_border'])
            worksheet.write(line_number, 1, invoice.number, styles['text_border'])
            worksheet.write(line_number, 2, invoice.create_date.split(' ')[0], styles['text_border'])
            worksheet.write(line_number, 3, invoice.partner_id.name, styles['text_border'])
            worksheet.write(line_number, 4, invoice.reference, styles['text_border'])
            worksheet.write(line_number, 5, invoice.payment_term_id.name or '', styles['text_border'])
            worksheet.write(line_number, 6, invoice.amount_untaxed, styles['number_border'])
            worksheet.write(line_number, 7, invoice.amount_total, styles['number_border'])
            worksheet.write(line_number, 8, montant_acomptes, styles['number_border'])
            worksheet.write(line_number, 9, solde, styles['number_bold_border'])
            line_number += 1

        # --- Ajout de la ligne de la dernière semaine ---
        if solde:
            worksheet.merge_range(line_number, 0, line_number, 5, u"Total sans date d'échéance" if date and not day
                                                                else u"Total de la date d'échéance " + date, styles['text_total_border'])
            for col in range(6, 9):
                worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
            worksheet.write(line_number, 9, solde, styles['number_total_border'])
            total.append(line_number)
            line_number += 1

        # --- Ligne de récap total ---
        if solde and total:
            worksheet.merge_range(line_number, 0, line_number, 5, 'Total', styles['text_title_border'])
            for col in range(6, 9):
                val = '=%s' % ('+'.join([xl_rowcol_to_cell(x, col) for x in total]))
                worksheet.write(line_number, col, val, styles['number_title_border'])
            worksheet.write(line_number, 9, solde, styles['number_title_border'])

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        self.file = base64.b64encode(data)
        return self._action_return()

    FUNDICT = {'encours': '_create_encours_excel',
               'echeancier' : '_create_echeancier_excel',
               'autre': '_dummy_function'}

    @api.multi
    def button_print(self):
        file_name = {'encours' : 'Encours des commandes de vente.xlsx',
                     'echeancier': u'Échéancier des règlements fournisseurs.xlsx',
                     'autre': 'Autre.xlsx'}
        self.file_name = file_name[self.report_model]
        return getattr(self, self.FUNDICT[self.report_model])()
