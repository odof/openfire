# -*- coding: utf-8 -*-

import base64
from datetime import datetime
from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_compare


class OfPurchaseReportWizard(models.TransientModel):
    _name = 'of.purchase.report.wizard'

    type = fields.Selection(
        [
            ('fnr', u"Facturé non réceptionné"),
            ('rnf', u"Réceptionné non facturé"),
        ], string=u"Modèle de rapport", required=True
    )
    file_name = fields.Char(string="Nom du fichier", compute="_compute_file_name", store=True)
    file = fields.Binary(string="Fichier")
    user_company_id = fields.Many2one('res.company', default=lambda s: s.env.user.company_id)
    company_ids = fields.Many2many('res.company', string=u'Sociétés', default=lambda s: s.env.user.company_id)
    date = fields.Date(u'Date de création', default=lambda self: datetime.now().strftime("%Y-%m-%d"))

    @api.depends('type')
    def _compute_file_name(self):
        selection_dict = dict(self._fields['type']._description_selection(self.env))
        self.file_name = selection_dict.get(self.type, 'rapport') + '.xlsx'

    @api.depends()
    def _compute_user_company_id(self):
        self.user_company_id = self.env.user.company_id

    @api.multi
    def _dummy_function(self):
        self.file = False
        return {"type": "ir.actions.do_nothing"}

    def _get_styles_excel(self, workbook):
        color_lighter_gray = '#DDDDDD'

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

        style_text_title_border = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bold': True,
            'font_size': 10,
            'bg_color': color_lighter_gray,
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

        style_number_border = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 8,
            'border': True,
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

        return {
            'text_border': style_text_border,
            'text_border_left': style_text_border_left,
            'text_title_border': style_text_title_border,
            'text_title_ita_border': style_text_title_ita_border,
            'text_title_border_wrap': style_text_title_border_wrap,
            'number_border': style_number_border,
            'number_title_border': style_number_title_border,
        }

    @api.model
    def get_lines_facture_non_receptionne(self):
        date_datetime_str = self.date + ' 23:59:59'
        self.env.cr.execute(
            "SELECT pol.id "
            "FROM purchase_order_line AS pol "
            "INNER JOIN product_product AS pp ON pp.id = pol.product_id "
            "INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id "
            "INNER JOIN ( "
            "  SELECT ail.purchase_line_id, ail.uom_id, SUM(ail.quantity) AS qty "
            "  FROM account_invoice AS ai "
            "  INNER JOIN account_invoice_line AS ail "
            "    ON ail.invoice_id = ai.id "
            "  WHERE ai.state IN ('open', 'paid') "
            "    AND ai.date_invoice <= %(date)s "
            "    AND ail.purchase_line_id IS NOT NULL "
            "  GROUP BY purchase_line_id, uom_id "
            ") AS ail ON ail.purchase_line_id = pol.id "
            "LEFT JOIN ( "
            "  SELECT purchase_line_id, product_uom, sum(product_uom_qty) AS qty "
            "  FROM stock_move "
            "  WHERE purchase_line_id IS NOT NULL "
            "  AND state = 'done' "
            "  AND date <= %(date)s "
            "  GROUP BY purchase_line_id, product_uom "
            ") AS sm ON sm.purchase_line_id = pol.id "
            "WHERE pt.type != 'service' "
            "AND pol.company_id IN %(company_ids)s "
            "AND pol.state IN ('purchase', 'done') "
            "AND COALESCE(sm.qty, 0) < ail.qty ",
            {'company_ids': self.company_ids._ids, 'date': date_datetime_str}
        )

        purchase_line_ids = [row[0] for row in self.env.cr.fetchall()]
        purchase_lines = self.env['purchase.order.line'].browse(purchase_line_ids)

        # Pour chaque ligne de commande, on vérifie les quantités livrées/facturées à la date.
        values = []
        for line in purchase_lines:
            if line.product_id.type == 'service':
                continue
            # Calcul de la quantité facturée
            qty_invoiced = 0.0
            price_invoiced = 0.0
            date_invoiced = ''
            for inv_line in line.invoice_lines:
                if inv_line.invoice_id.state in ('open', 'paid') and inv_line.invoice_id.date_invoice <= self.date:
                    if inv_line.invoice_id.type == 'in_invoice':
                        qty_invoiced += inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                        date_invoiced = max(date_invoiced, inv_line.invoice_id.date_invoice)
                    elif inv_line.invoice_id.type == 'in_refund':
                        qty_invoiced -= inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    price_invoiced += inv_line.price_subtotal_signed

            # Calcul de la quantité réceptionnée
            qty_received = 0.0
            date_received = ''
            if line.order_id.state not in ('purchase', 'done'):
                qty_received = 0.0
            elif line.product_id.type not in ('consu', 'product'):
                line.qty_received = line.product_qty
                date_received = line.date_order
            else:
                for move in line.move_ids:
                    if move.state == 'done' and move.date <= date_datetime_str:
                        if move.product_uom != line.product_uom:
                            qty_received += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                        else:
                            qty_received += move.product_uom_qty
                        date_received = max(date_received, move.date)

            if float_compare(qty_invoiced, qty_received, precision_rounding=line.product_uom.rounding) == 1:
                values.append((line, qty_invoiced, qty_received, date_invoiced, date_received, price_invoiced))
        return values

    @api.model
    def get_lines_receptionne_non_facture(self):
        date_datetime_str = self.date + ' 23:59:59'
        self.env.cr.execute(
            "SELECT pol.id "
            "FROM purchase_order_line AS pol "
            "INNER JOIN product_product AS pp ON pp.id = pol.product_id "
            "INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id "
            "INNER JOIN ("
            "  SELECT purchase_line_id, product_uom, sum(product_uom_qty) AS qty "
            "  FROM stock_move "
            "  WHERE purchase_line_id IS NOT NULL "
            "  AND ("
            "    state NOT IN ('done', 'cancel')"
            "    OR ("
            "      state = 'done' "
            "      AND date <= %(date)s "
            "    ) "
            "  ) "
            "  GROUP BY purchase_line_id, product_uom "
            ") AS sm ON sm.purchase_line_id = pol.id "
            "LEFT JOIN ("
            "  SELECT ail.purchase_line_id, ail.uom_id, SUM(ail.quantity) AS qty "
            "  FROM account_invoice AS ai "
            "  INNER JOIN account_invoice_line AS ail "
            "    ON ail.invoice_id = ai.id "
            "  WHERE ai.state IN ('open', 'paid') "
            "    AND ai.date_invoice <= %(date)s "
            "    AND ail.purchase_line_id IS NOT NULL "
            "  GROUP BY purchase_line_id, uom_id "
            ") AS ail ON ail.purchase_line_id = pol.id "
            "WHERE pt.type != 'service' "
            "AND pol.company_id IN %(company_ids)s "
            "AND pol.state IN ('purchase', 'done') "
            "AND sm.qty > COALESCE(ail.qty, 0) ",
            {'company_ids': self.company_ids._ids, 'date': date_datetime_str}
        )

        purchase_line_ids = [row[0] for row in self.env.cr.fetchall()]
        purchase_lines = self.env['purchase.order.line'].browse(purchase_line_ids)

        # Pour chaque ligne de commande, on vérifie les quantités livrées/facturées à la date.
        date_datetime_str = self.date + ' 23:59:59'
        values = []
        for line in purchase_lines:
            if line.product_id.type == 'service':
                continue
            # Calcul de la quantité facturée
            qty_invoiced = 0.0
            price_invoiced = 0.0
            date_invoiced = ''
            for inv_line in line.invoice_lines:
                if inv_line.invoice_id.state in ('open', 'paid') and inv_line.invoice_id.date_invoice <= self.date:
                    if inv_line.invoice_id.type == 'in_invoice':
                        qty_invoiced += inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                        date_invoiced = max(date_invoiced, inv_line.invoice_id.date_invoice)
                    elif inv_line.invoice_id.type == 'in_refund':
                        qty_invoiced -= inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    price_invoiced += inv_line.price_subtotal_signed

            # Calcul de la quantité réceptionnée
            qty_received = 0.0
            date_received = ''
            if line.order_id.state not in ('purchase', 'done'):
                qty_received = 0.0
            elif line.product_id.type not in ('consu', 'product'):
                line.qty_received = line.product_qty
                date_received = line.date_order
            else:
                for move in line.move_ids:
                    if move.state == 'done' and move.date <= date_datetime_str:
                        if move.product_uom != line.product_uom:
                            qty_received += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                        else:
                            qty_received += move.product_uom_qty
                        date_received = max(date_received, move.date)

            if qty_invoiced < qty_received:
                values.append((line, qty_invoiced, qty_received, date_invoiced, date_received, price_invoiced))
        return values

    @api.multi
    def _create_excel_report(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')

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
        worksheet.set_column(0, 0, 15)      # Largeur colonne "Société / Magasin"
        worksheet.set_column(1, 1, 13)      # Largeur colonne "Commande"
        worksheet.set_column(2, 2, 20)      # Largeur colonne "Fournisseur"
        worksheet.set_column(3, 3, 15)      # Largeur colonne "Réception prévue"
        worksheet.set_column(4, 4, 70)      # Largeur colonne "Article"
        worksheet.set_column(5, 5, 15)      # Largeur colonne "Qté commandée"
        worksheet.set_column(6, 6, 15)      # Largeur colonne "Qté reçue"
        worksheet.set_column(7, 7, 15)      # Largeur colonne "Qté facturée"
        worksheet.set_column(8, 8, 15)      # Largeur colonne "Date de réception"
        worksheet.set_column(9, 9, 15)      # Largeur colonne "Date de facturation"
        worksheet.set_column(10, 10, 10)    # Largeur colonne "Prix d'achat"
        worksheet.set_column(11, 11, 10)    # Largeur colonne "Prix facturé"

        # --- Entête ---
        worksheet.merge_range(0, 0, 0, 3, "Nom du fichier", styles['text_title_ita_border'])
        worksheet.merge_range(0, 4, 0, 7, u"Date de l'analyse", styles['text_title_ita_border'])
        worksheet.merge_range(0, 8, 0, 11, u"Société(s)", styles['text_title_ita_border'])
        worksheet.merge_range(1, 0, 1, 3, self.file_name.split('.')[0], styles['text_title_border'])
        worksheet.merge_range(1, 4, 1, 7, self.date, styles['text_title_border'])
        worksheet.merge_range(1, 8, 1, 11, ", ".join(self.company_ids.mapped('name')), styles['text_title_border_wrap'])

        # --- Ajout des lignes ---
        line_number = 3
        worksheet.write(line_number, 0, u"Société / Magasin", styles['text_title_border'])
        worksheet.write(line_number, 1, "Commande", styles['text_title_border'])
        worksheet.write(line_number, 2, "Fournisseur", styles['text_title_border'])
        worksheet.write(line_number, 3, u"Réception prévue", styles['text_title_border'])
        worksheet.write(line_number, 4, "Article", styles['text_title_border'])
        worksheet.write(line_number, 5, u"Qté commandée", styles['text_title_border'])
        worksheet.write(line_number, 6, u"Qté reçue", styles['text_title_border'])
        worksheet.write(line_number, 7, u"Qté facturée", styles['text_title_border'])
        worksheet.write(line_number, 8, u"Date de réception", styles['text_title_border'])
        worksheet.write(line_number, 9, "Date de facturation", styles['text_title_border'])
        worksheet.write(line_number, 10, "Prix d'achat", styles['text_title_border'])
        worksheet.write(line_number, 11, u"Prix facturé", styles['text_title_border'])
        line_number += 1

        if self.type == 'fnr':
            values = self.get_lines_facture_non_receptionne()
        elif self.type == 'rnf':
            values = self.get_lines_receptionne_non_facture()
        else:
            raise UserError(u"Le modèle de document demandé n'est pas reconnu.")

        tab_first_line = line_number
        for line, qty_invoiced, qty_received, date_invoiced, date_received, price_invoiced in values:
            # Société / Magasin
            worksheet.write(line_number, 0, line.company_id.name, styles['text_border'])
            # Numéro de commande
            worksheet.write(line_number, 1, line.order_id.name, styles['text_border'])
            # Fournisseur
            worksheet.write(line_number, 2, line.order_id.partner_id.name, styles['text_border'])
            # Date de réception prévue
            worksheet.write(
                line_number, 3,
                line.date_planned and fields.Date.from_string(line.date_planned).strftime(lang.date_format),
                styles['text_border'])
            # Article
            worksheet.write(line_number, 4, line.name.split('\n')[0], styles['text_border_left'])
            # Quantité commandée
            worksheet.write(line_number, 5, line.product_qty, styles['number_border'])
            # Quantité reçue
            worksheet.write(line_number, 6, qty_received, styles['number_border'])
            # Quantité facturée
            worksheet.write(line_number, 7, qty_invoiced, styles['number_border'])
            # Date de réception
            worksheet.write(
                line_number, 8,
                date_received and fields.Date.from_string(date_received).strftime(lang.date_format),
                styles['text_border'])
            # Date de facturation
            worksheet.write(
                line_number, 9,
                date_invoiced and fields.Date.from_string(date_invoiced).strftime(lang.date_format),
                styles['text_border'])
            # Prix d'achat
            worksheet.write(line_number, 10, line.price_subtotal, styles['number_border'])
            # Prix facturé
            worksheet.write(line_number, 11, round(price_invoiced, 2), styles['number_border'])

            line_number += 1

        worksheet.write(line_number, 9, "Total", styles['text_title_border'])
        worksheet.write(
            line_number, 10,
            '=SUM(%s:%s)' % (xl_rowcol_to_cell(tab_first_line, 10),
                             xl_rowcol_to_cell(line_number - 1, 10)),
            styles['number_title_border'])
        worksheet.write(
            line_number, 11,
            '=SUM(%s:%s)' % (xl_rowcol_to_cell(tab_first_line, 11),
                             xl_rowcol_to_cell(line_number - 1, 11)),
            styles['number_title_border'])

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        return base64.b64encode(data)

    FUNDICT = {
        'rnf': '_create_excel_report',
        'fnr': '_create_excel_report',
    }

    # Grâce au return do_nothing
    # on peut appuyer sur le bouton et ne pas avoir à renvoyer la vue
    # pour mettre à jour les informations
    @api.multi
    def button_print(self):
        self.file = getattr(self, self.FUNDICT[self.type])()
        return {"type": "ir.actions.do_nothing"}
