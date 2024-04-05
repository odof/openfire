# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging

from odoo import api, fields, models
from odoo.tools import float_compare

from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

_logger = logging.getLogger(__name__)


class OFStockInventoryValuation(models.TransientModel):
    _name = 'of.stock.inventory.valuation'
    _description = u"Rapport d'inventaire valorisé"

    @api.model
    def _default_allowed_company_ids(self):
        return self.env['stock.location'].search([('usage', '=', 'internal')]).mapped('company_id')

    allowed_company_ids = fields.Many2many(
        comodel_name='res.company', default=lambda self: self._default_allowed_company_ids(),
        compute='_compute_allowed_company_ids')
    company_id = fields.Many2one(
        comodel_name='res.company', string=u"Société", required=True,
        domain="[('id', 'in', allowed_company_ids[0][2])]")
    date = fields.Datetime(string="Date de stock", required=True)
    brand_ids = fields.Many2many(comodel_name='of.product.brand', string="Marques")
    categ_ids = fields.Many2many(comodel_name='product.category', string=u"Catégories")
    file = fields.Binary(string='Fichier')
    file_name = fields.Char(string='Nom du fichier', default=u"inventaire_valorisé.xlsx")
    inventory_ids = fields.Many2many(
        comodel_name='stock.inventory', string="Inventaires",
        domain="[('state', '=', 'confirm'), "
               "('location_id', 'in', location_ids and location_ids[0] and location_ids[0][2] or False)]",
        help=u"Si renseigné, le rapport incluera les  nouvelles valeurs après application des inventaires.")
    location_ids = fields.Many2many(
        comodel_name='stock.location', string="Emplacements", required=True,
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]")

    def _compute_allowed_company_ids(self):
        companies = self.env['stock.location'].search([('usage', '=', 'internal')]).mapped('company_id')
        for wizard in self:
            wizard.allowed_company_ids = companies

    @api.onchange('location_ids')
    def _onchange_location_ids(self):
        for wizard in self:
            wizard.inventory_ids = wizard.inventory_ids.filtered(lambda inv: inv.location_id in wizard.location_ids)
        self.update({'location_ids': False})

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.update({'location_ids': False})

    @api.model
    def _get_styles_excel(self, workbook):
        color_lighter_gray = '#DDDDDD'
        color_green = '#008000'
        color_red = '#800000'

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

        style_number_border_green = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 8,
            'border': True,
            'font_color': color_green,
        })

        style_number_border_red = workbook.add_format({
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 8,
            'border': True,
            'font_color': color_red,
        })

        return {
            'text_border_left': style_text_border_left,
            'text_title_border': style_text_title_border,
            'text_title_border_wrap': style_text_title_border_wrap,
            'text_title_ita_border': style_text_title_ita_border,
            'text_total_border': style_text_total_border,
            'number_border': style_number_border,
            'number_border_green': style_number_border_green,
            'number_border_red': style_number_border_red,
        }

    def get_stock_history(self):
        self.ensure_one()
        product_obj = self.env['product.product']

        # Requêtes SQL basées sur la vue stock_history du module stock_account
        query_in = """
            SELECT
                stock_move.location_dest_id AS location_id,
                stock_move.product_id AS product_id,
                quant.qty AS quantity,
                quant.cost as price_unit_on_quant,
                stock_production_lot.of_internal_serial_number AS of_internal_serial_number
            FROM
                stock_quant as quant
            JOIN
                stock_quant_move_rel ON stock_quant_move_rel.quant_id = quant.id
            JOIN
                stock_move ON stock_move.id = stock_quant_move_rel.move_id
            LEFT JOIN
                stock_production_lot ON stock_production_lot.id = quant.lot_id
            JOIN
                product_product ON product_product.id = stock_move.product_id
            JOIN
                product_template ON product_template.id = product_product.product_tmpl_id
            WHERE
                quant.qty>0
                AND stock_move.state = 'done'
                AND stock_move.date <= %(date)s
                AND stock_move.location_dest_id IN %(location_ids)s
                AND stock_move.location_dest_id != stock_move.location_id"""
        query_out = """
            SELECT
                stock_move.location_id AS location_id,
                stock_move.product_id AS product_id,
                - quant.qty AS quantity,
                quant.cost as price_unit_on_quant,
                stock_production_lot.of_internal_serial_number AS of_internal_serial_number
            FROM
                stock_quant as quant
            JOIN
                stock_quant_move_rel ON stock_quant_move_rel.quant_id = quant.id
            JOIN
                stock_move ON stock_move.id = stock_quant_move_rel.move_id
            LEFT JOIN
                stock_production_lot ON stock_production_lot.id = quant.lot_id
            JOIN
                product_product ON product_product.id = stock_move.product_id
            JOIN
                product_template ON product_template.id = product_product.product_tmpl_id
            WHERE
                quant.qty>0
                AND stock_move.state = 'done'
                AND stock_move.date <= %(date)s
                AND stock_move.location_id IN %(location_ids)s
                AND stock_move.location_id != stock_move.location_dest_id"""

        query_params = {
            'date': self.date,
            'location_ids': self.location_ids._ids,
        }
        if self.brand_ids:
            query_brand = """
                AND product_template.brand_id IN %(brand_ids)s"""
            query_in += query_brand
            query_out += query_brand
            query_params['brand_ids'] = self.brand_ids._ids
        if self.categ_ids:
            query_brand = """
                AND product_template.categ_id IN %(categ_ids)s"""
            query_in += query_brand
            query_out += query_brand
            query_params['categ_ids'] = self.categ_ids._ids

        query = """
            SELECT
                location_id,
                product_id,
                SUM(quantity) as quantity,
                COALESCE(SUM(price_unit_on_quant * quantity), 0) AS price,
                of_internal_serial_number
            FROM
                ((""" + query_in + """
                ) UNION ALL
                (""" + query_out + """
                )) AS foo
            GROUP BY location_id, product_id, of_internal_serial_number"""

        self.env.cr.execute(query, query_params)

        stock_history_dict = {loc_id: {} for loc_id in self.location_ids.ids}
        for h in self.env.cr.dictfetchall():
            product_vals = stock_history_dict[h['location_id']].setdefault(h['product_id'], {})
            product_vals[h['of_internal_serial_number'] or False] = h

        for product_dict in stock_history_dict.itervalues():
            # On met tous les articles en cache pour favoriser les calculs en lots
            product_obj.browse(product_dict)
            # On met à jour le prix des articles en fonction des règles de calcul
            for product_id, serial_dict in product_dict.iteritems():
                product = product_obj.browse(product_id)
                if product.cost_method != 'real':
                    price_unit = product.get_history_price(self.company_id.id, date=self.date)
                    for hist_vals in serial_dict.itervalues():
                        hist_vals['price'] = hist_vals['quantity'] * price_unit

        if self.inventory_ids:
            product_domain = []
            if self.brand_ids:
                product_domain = [('brand_id', 'in', self.brand_ids.ids)]
            if self.categ_ids:
                product_domain += [('categ_id', 'in', self.categ_ids.ids)]
            if product_domain:
                # Potentiellement beaucoup d'articles inutiles,
                # on ne veut pas calculer toutes leurs valeurs par la suite, donc on bloque le prefetch
                all_products = product_obj.with_context(active_test=False, prefetch_fields=False).search(product_domain)
                product_domain = [('product_id', 'in', all_products.ids)]
            price_precision = self.env['decimal.precision'].precision_get('Product Price')
            for inv_line in self.env['stock.inventory.line'].search(
                    [('inventory_id', 'in', self.inventory_ids.ids)] + product_domain):
                vals_dict = stock_history_dict[inv_line.location_id.id].setdefault(inv_line.product_id.id, {})
                if inv_line.of_internal_serial_number in vals_dict:
                    vals_dict = vals_dict[inv_line.of_internal_serial_number]
                    vals_dict['inv_qty'] = vals_dict.get('inv_qty', 0) + inv_line.product_qty
                else:
                    vals_dict[inv_line.of_internal_serial_number] = {
                        'product_id': inv_line.product_id.id,
                        'of_internal_serial_number': inv_line.of_internal_serial_number,
                        'quantity': 0,
                        'price': 0,
                        'location_id': inv_line.location_id.id,
                        'inv_qty': inv_line.product_qty,
                    }
                    vals_dict = vals_dict[inv_line.of_internal_serial_number]
                # Pour simplifier le calcul de la valeur des articles de l'ajustement, on utilise le prix moyen des
                # articles en stock
                if vals_dict['quantity']:
                    vals_dict['inv_value'] = round(
                        vals_dict['price'] * vals_dict['inv_qty'] / vals_dict['quantity'], price_precision)
                else:
                    # Il n'y a pas d'article en stock, on prend le coût de l'article à date
                    price_unit = inv_line.product_id.get_history_price(self.company_id.id, date=self.date)
                    vals_dict['inv_value'] = round(price_unit * vals_dict['inv_qty'], price_precision)

        return stock_history_dict

    @api.multi
    def action_generate_excel_file(self):
        product_obj = self.env['product.product'].with_context(active_test=False)

        # --- Ouverture du workbook ---
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})

        # --- Récupération de styles ---
        styles = self._get_styles_excel(workbook)

        # --- Création de la page ---
        worksheet = workbook.add_worksheet(u"Inventaire valorisé " + self.date)
        worksheet.set_paper(9)  # Format d'impression A4
        worksheet.set_landscape()  # Format d'impression paysage
        worksheet.set_margins(left=0.35, right=0.35, top=0.2, bottom=0.2)

        # --- Initialisation des colonnes ---
        worksheet.set_column(0, 0, 13)   # Largeur colonne 'Emplacement'
        worksheet.set_column(1, 1, 75)   # Largeur colonne 'Article'
        worksheet.set_column(2, 2, 13)   # Largeur colonne 'Catégorie'
        worksheet.set_column(3, 3, 13)   # Largeur colonne 'Marque'
        worksheet.set_column(4, 4, 50)   # Largeur colonne 'N° de série interne'
        worksheet.set_column(5, 5, 13)   # Largeur colonne 'Quantité (à date)'
        worksheet.set_column(6, 6, 13)   # Largeur colonne 'Valorisation (à date)'
        worksheet.set_column(7, 7, 13)   # Largeur colonne 'Quantité (ajustement)'
        worksheet.set_column(8, 8, 13)   # Largeur colonne 'Valorisation (ajustement)'
        worksheet.set_column(9, 7, 13)   # Largeur colonne 'Quantité (Valeur définitive)'
        worksheet.set_column(10, 8, 13)  # Largeur colonne 'Valorisation (Valeur définitive)'

        # --- Entête ---
        worksheet.merge_range(0, 0, 0, 2, u"Nom du fichier", styles['text_title_ita_border'])
        worksheet.merge_range(0, 3, 0, 5, u"Date de l'inventaire", styles['text_title_ita_border'])
        worksheet.merge_range(0, 6, 0, 10, u"Société", styles['text_title_ita_border'])
        worksheet.merge_range(1, 0, 1, 2, u"Inventaire valorisé", styles['text_title_border'])
        worksheet.merge_range(
            1, 3, 1, 5,
            self._fields['date'].convert_to_display_name(self.date, self),
            styles['text_title_border'])
        worksheet.merge_range(1, 6, 1, 10, self.company_id.name, styles['text_title_border_wrap'])

        # --- Ajout des lignes ---
        line_number = 3
        worksheet.merge_range(line_number, 0, line_number + 1, 0, u"Emplacement", styles['text_title_border'])
        worksheet.merge_range(line_number, 1, line_number + 1, 1, u"Article", styles['text_title_border'])
        worksheet.merge_range(line_number, 2, line_number + 1, 2, u"Catégorie", styles['text_title_border'])
        worksheet.merge_range(line_number, 3, line_number + 1, 3, u"Marque", styles['text_title_border'])
        worksheet.merge_range(line_number, 4, line_number + 1, 4, u"N° de série interne", styles['text_title_border'])
        worksheet.merge_range(line_number, 5, line_number, 6, u"Stock réel", styles['text_title_ita_border'])
        worksheet.merge_range(line_number, 7, line_number, 8, u"Ajustement de stock", styles['text_title_ita_border'])
        worksheet.merge_range(line_number, 9, line_number, 10, u"Total", styles['text_title_ita_border'])

        line_number += 1
        worksheet.write(line_number, 5, u"Quantité", styles['text_title_border'])
        worksheet.write(line_number, 6, u"Valorisation", styles['text_title_border'])
        worksheet.write(line_number, 7, u"Quantité", styles['text_title_border'])
        worksheet.write(line_number, 8, u"Valorisation", styles['text_title_border'])
        worksheet.write(line_number, 9, u"Quantité", styles['text_title_border'])
        worksheet.write(line_number, 10, u"Valorisation", styles['text_title_border'])

        line_number += 1

        all_data = self.get_stock_history()
        location_names = dict(self.location_ids.name_get())
        all_products = product_obj
        for product_dict in all_data.itervalues():
            all_products |= product_obj.browse(product_dict)
        product_names = dict(all_products.name_get())
        for location in self.location_ids:
            loc_data = all_data[location.id]
            loc_name = location_names[location.id]
            # Fonction search pour ordonner les articles
            for product in product_obj.search([('id', 'in', loc_data.keys())]):
                product_data = loc_data[product.id]
                prod_name = product_names[product.id]
                for serial in sorted(product_data.keys()):
                    vals = product_data[serial]
                    if not vals['quantity'] and not vals.get('inv_qty'):
                        continue
                    worksheet.write(line_number, 0, loc_name, styles['text_border_left'])
                    worksheet.write(line_number, 1, prod_name, styles['text_border_left'])
                    worksheet.write(line_number, 2, product.categ_id.name, styles['text_border_left'])
                    worksheet.write(line_number, 3, product.brand_id.name, styles['text_border_left'])
                    worksheet.write(line_number, 4, serial or '', styles['text_border_left'])
                    worksheet.write(line_number, 5, vals['quantity'], styles['number_border'])
                    worksheet.write(line_number, 6, vals['price'], styles['number_border'])

                    inv_color_name = ('number_border', 'number_border_red', 'number_border_green')
                    qty_color = inv_color_name[
                        float_compare(vals['quantity'], vals['inv_qty'], precision_rounding=product.uom_id.rounding)
                        if 'inv_qty' in vals
                        else 0
                    ]
                    worksheet.write(line_number, 7, vals.get('inv_qty', ''), styles[qty_color])

                    value_color = inv_color_name[
                        float_compare(
                            vals['price'], vals['inv_value'], precision_rounding=product.uom_id.rounding)
                        if 'inv_value' in vals
                        else 0
                    ]
                    worksheet.write(line_number, 8, vals.get('inv_value', ''), styles[value_color])

                    worksheet.write_formula(
                        line_number, 9,
                        "=IF(ISBLANK(%s),%s,%s)" % (
                            xl_rowcol_to_cell(line_number, 7),
                            xl_rowcol_to_cell(line_number, 5),
                            xl_rowcol_to_cell(line_number, 7),
                        ),
                        styles['number_border'],
                        value=vals.get('inv_qty', vals['quantity'])
                    )
                    worksheet.write_formula(
                        line_number, 10,
                        "=IF(ISBLANK(%s),%s,%s)" % (
                            xl_rowcol_to_cell(line_number, 8),
                            xl_rowcol_to_cell(line_number, 6),
                            xl_rowcol_to_cell(line_number, 8),
                        ),
                        styles['number_border'],
                        value=vals.get('inv_value', vals['price'])
                    )
                    line_number += 1

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()

        self.file = base64.encodestring(data)

        action = self.env.ref('of_sale_stock.action_of_stock_inventory_valuation').read()[0]
        action['views'] = [(self.env.ref('of_sale_stock.of_stock_inventory_valuation_view_form').id, 'form')]
        action['res_id'] = self.ids[0]
        return action
