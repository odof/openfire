# -*- coding: utf-8 -*-

import base64
from datetime import datetime
from odoo import models, fields, api
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
        return result

    file_name = fields.Char('Nom du fichier', size=64, default=u'Encours des commandes de vente.xlsx')
    file = fields.Binary('file')
    company_ids = fields.Many2many('res.company', string=u'Sociétés')
    user_company_id = fields.Many2one('res.company', compute="_compute_company_id")
    date = fields.Date(u'Date de création', default=datetime.now().strftime("%Y-%m-%d"))
    report_model = fields.Selection(_get_allowed_report_types, string=u"Modèle de rapport", required=True)
    period_n = fields.Many2one('date.range', string=u"Principale")
    period_n1 = fields.Many2one('date.range', string=u"À comparer")
    product_ids = fields.Many2many('product.template', string="Articles")
    partner_ids = fields.Many2many('res.partner', string="Clients")
    category_ids = fields.Many2many('product.category', string=u"Catégories d'articles")
    stats_partner = fields.Boolean(string="Stats/articles/clients", default=True)
    stats_product = fields.Boolean(string=u"Stats/clients/catégories d'articles", default=True)
    filtre_client = fields.Boolean(string="Filtre par client")
    filtre_article = fields.Boolean(string="Filtre par article")

    @api.depends('report_model')
    def _compute_company_id(self):
        user_obj = self.env['res.users']
        user = user_obj.browse(self._uid)
        self.user_company_id = user.company_id

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
        # color_light_gray = '#C0C0C0'
        color_lighter_gray = '#DDDDDD'
        color_light_blue = '#66FFFF'
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
            'bg_color' : color_lighter_gray,
        })

        style_text_title_border_blue = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_light_blue,
        })

        style_text_title_border_blue_left = workbook.add_format({
            'valign': 'vcenter',
            'align': 'left',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_light_blue,
        })

        style_text_title_border_red = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 13.5,
            'bg_color' : color_lighter_gray,
            'font_color': color_red,
        })

        style_text_title_border_wrap = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'text_wrap': True,
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_lighter_gray,
        })

        style_text_title_ita_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'italic': True,
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_lighter_gray,
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
            'bg_color' : color_lighter_gray,
            'num_format': '#,##0.00',
        })

        style_number_title_border_blue = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_light_blue,
            'num_format': '#,##0.00',
        })

        style_number_title_border_red = workbook.add_format({
            'valign': 'vcenter',
            'align': 'right',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color' : color_red,
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
            'text_border_left': style_text_border_left,
            'text_bold_border': style_text_bold_border,
            'text_title_border': style_text_title_border,
            'text_title_border_blue': style_text_title_border_blue,
            'text_title_border_blue_left': style_text_title_border_blue_left,
            'text_title_border_red': style_text_title_border_red,
            'text_title_ita_border': style_text_title_ita_border,
            'text_title_border_wrap': style_text_title_border_wrap,
            'text_total_border': style_text_total_border,
            'number_border': style_number_border,
            'number_bold_border': style_number_bold_border,
            'number_title_border': style_number_title_border,
            'number_title_border_blue': style_number_title_border_blue,
            'number_title_border_red': style_number_title_border_red,
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
        worksheet.set_column(7, 7, 25)      # Largeur colonne 'Accompte(s) versé(s) (total)'
        worksheet.set_column(8, 8, 20)      # Largeur colonne 'Solde'

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
        worksheet.write(line_number, 2, u'Pose prévisionnelle', styles['text_title_border'])
        worksheet.write(line_number, 3, 'Nom du client', styles['text_title_border'])
        worksheet.write(line_number, 4, 'Vendeur', styles['text_title_border'])
        worksheet.write(line_number, 5, 'Total HT', styles['text_title_border'])
        worksheet.write(line_number, 6, 'Total TTC', styles['text_title_border'])
        worksheet.write(line_number, 7, u'Accompte(s) versé(s) (total)', styles['text_title_border'])
        worksheet.write(line_number, 8, 'solde', styles['text_title_border'])
        line_number += 1
        solde = 0
        week, total = [], []
        order_domain = [('state', '!=', 'draft')]
        if self.company_ids._ids:
            order_domain = (order_domain and ['&']) + [('company_id', 'in', self.company_ids._ids)] + order_domain
        orders = self.env['sale.order'].search(order_domain).sorted(key=lambda r: r.of_date_de_pose)
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
                worksheet.merge_range(line_number, 0, line_number, 4,
                                      u'Total sans date de pose prévisionnelle' if date and week and not week[-1] else 'Total de la semaine ' + week[-1],
                                      styles['text_total_border'])
                week.append(date)
                for col in range(5, 9):
                    worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
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
            worksheet.merge_range(line_number, 0, line_number, 4,
                                  u'Total sans date de pose prévisionnelle' if not week[-1] and not date else 'Total de la semaine ' + week[-1],
                                  styles['text_total_border'])
            for col in range(5, 9):
                worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
            total.append(line_number)
            line_number += 1

        # --- Ligne de récap total ---
        if solde and total:
            worksheet.merge_range(line_number, 0, line_number, 4, 'Total de toute les semaines', styles['text_title_border'])
            for col in range(5, 9):
                val = '=%s' % ('+'.join([xl_rowcol_to_cell(x, col) for x in total]))
                worksheet.write(line_number, col, val, styles['number_title_border'])

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
        invoice_domain = [('type', '=', 'in_invoice')]
        if self.company_ids._ids:
            invoice_domain = (invoice_domain and ['&']) + [('company_id', 'in', self.company_ids._ids)] + invoice_domain
        invoices = self.env['account.invoice'].search(invoice_domain).sorted(key=lambda r: r.date_due)
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
                worksheet.merge_range(line_number, 0, line_number, 5,
                                      u"Total sans date d'échéance" if date and not day[-1] else u"Total de la date d'échéance " + day[-1],
                                      styles['text_total_border'])
                day.append(date)
                for col in range(6, 10):
                    worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
                total.append(line_number)
                line_number += 1
                line_keep = line_number

            # --- lignes régulières ---
            solde = invoice.amount_total - montant_acomptes
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
            worksheet.merge_range(line_number, 0, line_number, 5,
                                  u"Total sans date d'échéance" if date and not day else u"Total de la date d'échéance " + date,
                                  styles['text_total_border'])
            for col in range(6, 10):
                worksheet.write(line_number, col, '=SUM(%s)' % xl_range(line_keep, col, line_number - 1, col), styles['number_total_border'])
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
        self.file = base64.b64encode(data)
        return self._action_return()

    @api.multi
    def _create_stats_excel(self):
        # --- Ouverture du workbook ---
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})

        # --- Couleur de police ---
        styles = self._get_styles_excel(workbook)

        #  Création des domaines
        sale_order_domain = [
            ('state', '!=', 'draft'),
            '|',
            '&', ('confirmation_date', '>=', self.period_n.date_start), ('confirmation_date', '<=', self.period_n.date_end),
            '&', ('confirmation_date', '>=', self.period_n1.date_start), ('confirmation_date', '<=', self.period_n1.date_end)]

        if self.company_ids:
            sale_order_domain += [('company_id', 'in', self.company_ids._ids)]
        if self.partner_ids and self.filtre_client:
            sale_order_domain += [('partner_id', 'in', self.partner_ids._ids)]
        line_domain = []
        if self.product_ids and self.filtre_article:
            line_domain += [('product_id', 'in', self.product_ids._ids)]
        if self.category_ids and self.filtre_article:
            line_domain += [('product_id.categ_id', 'child_of', self.category_ids._ids)]

        orders = self.env['sale.order'].search(sale_order_domain)
        line_domain += [('order_id', 'in', orders._ids)]
        lines = self.env['sale.order.line'].search(line_domain).sorted('order_partner_id')

        vals = {}  # must be vals = {client: {produit: {period_n:{qty: x, prix:y}, period_n1:{qty: x, prix:y}}, qté: 'x'}}
        vals2 = {}  # must be vals2 = {categ: {client: {period_n:{qty: x, prix:y}, period_n1:{qty: x, prix:y}}, qté: 'x'}}

        # Récupération des valeurs dans les dictionnaires
        for line in lines:
            if line.product_uom_qty == 0:
                continue

            if line.order_partner_id not in vals:
                vals[line.order_partner_id] = {'qté': 0}
            valeurs = vals[line.order_partner_id]
            if line.product_id not in valeurs:
                valeurs[line.product_id] = {self.period_n: {'qté': 0, 'prix': 0}, self.period_n1: {'qté': 0, 'prix': 0}}
            valeurs = valeurs[line.product_id]

            if line.product_id.categ_id not in vals2:
                vals2[line.product_id.categ_id] = {'qté': 0}
            valeurs2 = vals2[line.product_id.categ_id]
            categ = line.product_id.categ_id
            if line.order_partner_id not in valeurs2:
                valeurs2[line.order_partner_id] = {self.period_n: {'qté': 0, 'prix': 0}, self.period_n1: {'qté': 0, 'prix': 0}}
            valeurs2 = valeurs2[line.order_partner_id]

            if line.order_id.confirmation_date >= self.period_n.date_start and line.order_id.confirmation_date <= self.period_n.date_end:
                vals[line.order_partner_id]['qté'] += line.product_uom_qty
                vals2[categ]['qté'] += line.product_uom_qty
                valeurs[self.period_n]['qté'] += line.product_uom_qty
                valeurs[self.period_n]['prix'] += line.price_unit * line.product_uom_qty
                valeurs2[self.period_n]['qté'] += line.product_uom_qty
                valeurs2[self.period_n]['prix'] += line.price_unit * line.product_uom_qty

            else:
                valeurs[self.period_n1]['qté'] += line.product_uom_qty
                valeurs[self.period_n1]['prix'] += line.price_unit * line.product_uom_qty
                valeurs2[self.period_n1]['qté'] += line.product_uom_qty
                valeurs2[self.period_n1]['prix'] += line.price_unit * line.product_uom_qty

        # un premier tri qui permet d'avoir les tableaux dans l'ordre décroissant
        sorted_partner = sorted(vals.items(), key=lambda data: data[1]['qté'], reverse=True)
        sorted_categ = sorted(vals2.items(), key=lambda data: data[1]['qté'], reverse=True)

        stats = {}
        if self.stats_partner:
            stats['partner'] = (sorted_partner, 'Statistiques de ventes par client')
        if self.stats_product:
            stats['categ'] = (sorted_categ, u'Statistiques de ventes par catégorie de produit')

        for page in stats:
            values, name = stats[page]

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
            worksheet.set_column(6, 6, 12)      # Largeur colonne 'Evo % CA'

            worksheet.merge_range(0, 0, 0, 1, 'Nom du fichier', styles['text_title_ita_border'])
            worksheet.merge_range(0, 2, 0, 5, u'Date de création', styles['text_title_ita_border'])
            worksheet.merge_range(0, 6, 0, 8, u'Société(s)' , styles['text_title_ita_border'])
            worksheet.merge_range(0, 9, 0, 11, u'Périodes : N / N-1' , styles['text_title_ita_border'])
            worksheet.merge_range(1, 0, 1, 1, name, styles['text_title_border'])
            worksheet.merge_range(1, 2, 1, 5, self.date, styles['text_title_border'])
            worksheet.merge_range(1, 6, 1, 8, ", ".join(self.company_ids.mapped('name')), styles['text_title_border_wrap'])
            worksheet.merge_range(1, 9, 1, 11, self.period_n.name + ' / ' + self.period_n1.name, styles['text_title_border_wrap'])

            line_number = 3

            for obj, valeurs in values:
                del valeurs['qté']  # On a plus besoin de la quantité dans le dictionnaire donc on l'enlève pour pouvoir trier correctement
                worksheet.merge_range(line_number, 0, line_number + 1, 0, obj.name, styles['text_title_border_red'])
                worksheet.merge_range(line_number, 1, line_number, 3,  u'Qté - Commandes en cours', styles['text_title_border'])
                worksheet.merge_range(line_number, 4, line_number, 6, u'CA', styles['text_title_border'])
                line_number += 1
                worksheet.write(line_number, 1, 'N', styles['text_title_border'])
                worksheet.write(line_number, 2, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 3, 'Evo %', styles['text_title_border'])
                worksheet.write(line_number, 4, 'N', styles['text_title_border'])
                worksheet.write(line_number, 5, 'N-1', styles['text_title_border'])
                worksheet.write(line_number, 6, 'Evo %', styles['text_title_border'])
                line_number += 1
                line_keep = line_number
                valeurs = sorted(valeurs.items(), key=lambda data: data[1][self.period_n1]['qté'])  # Tri secondaire par period_n1 croissant
                valeurs = sorted(valeurs, key=lambda data: data[1][self.period_n]['qté'], reverse=True)  # Tri principal par period_n décroissant
                for entry, data in valeurs:
                    qty_n = data[self.period_n]['qté']
                    qty_n1 = data[self.period_n1]['qté']
                    price_n = data[self.period_n]['prix']
                    price_n1 = data[self.period_n1]['prix']
                    worksheet.write(line_number, 0, entry.name, styles['text_border_left'])
                    worksheet.write(line_number, 1, qty_n, styles['number_border'])
                    worksheet.write(line_number, 2, qty_n1, styles['number_border'])
                    worksheet.write(line_number, 3, '=(%s / %s - 1) * 100' % (xl_rowcol_to_cell(line_number, 1),
                                                                              xl_rowcol_to_cell(line_number, 2)) if qty_n1 else 100, styles['number_border'])
                    worksheet.write(line_number, 4, price_n, styles['number_border'])
                    worksheet.write(line_number, 5, price_n1, styles['number_border'])
                    worksheet.write(line_number, 6, '=(%s / %s - 1) * 100' % (xl_rowcol_to_cell(line_number, 4),
                                                                              xl_rowcol_to_cell(line_number, 5)) if price_n1 else 100, styles['number_border'])
                    line_number += 1
                worksheet.write(line_number, 0, 'TOTAL', styles['text_title_border_blue_left'])
                for column in range(1, 7):
                    if column in (3, 6):
                        worksheet.write(line_number, column, '=IF(%s>0,(%s / %s - 1) * 100,100)' % (xl_rowcol_to_cell(line_number, column-1),
                                                                                                    xl_rowcol_to_cell(line_number, column-2),
                                                                                                    xl_rowcol_to_cell(line_number, column-1)), styles['number_title_border_blue'])
                    else:
                        worksheet.write(line_number, column, '=SUM(%s:%s)' % (xl_rowcol_to_cell(line_keep, column),
                                                                              xl_rowcol_to_cell(line_number - 1, column)), styles['number_title_border_blue'])
                line_number += 2

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        self.file = base64.b64encode(data)
        return self._action_return()

    FUNDICT = {
        'encours' : '_create_encours_excel',
        'echeancier' : '_create_echeancier_excel',
        'stats' : '_create_stats_excel',
        'autre' : '_dummy_function'
    }

    @api.multi
    def button_print(self):
        file_name = {
            'encours' : 'Encours des commandes de vente.xlsx',
            'echeancier': u'Échéancier des règlements fournisseurs.xlsx',
            'stats' : "Statistiques de ventes.xlsx",
            'autre': 'Autre.xlsx'
        }
        self.file_name = file_name[self.report_model]
        return getattr(self, self.FUNDICT[self.report_model])()
