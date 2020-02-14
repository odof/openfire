# -*- coding: utf-8 -*-
from odoo import api, fields, models
import base64
from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_range, xl_rowcol_to_cell


class OFRapportGestionStockWizard(models.TransientModel):
    _name = "of.rapport.gestion.stock.wizard"

    product_ids = fields.Many2many('product.product', string=u"Articles")
    file = fields.Binary(string='Fichier')
    file_name = fields.Char(string='Nom du fichier', size=64, default='articles.xlsx')
    location_ids = fields.Many2many(
        'stock.location', string="Emplacement", required=True, domain=[('usage', '=', 'internal')])
    date_stock = fields.Date(string='Date stock', required=True)

    prix = fields.Float(string="PV", help="Prix de vente minimum")
    brand_ids = fields.Many2many('of.product.brand', string=u"Marques")
    categ_ids = fields.Many2many('product.category', string=u"Catégories")
    active_product = fields.Boolean(
        string="Articles actifs", help=u"Articles en stock ou présents dans un BL/BR en cours")

    @api.multi
    def action_generate_excel_file(self):
        self.ensure_one()
        display_client_order_ref = self._context.get('display_client_order_ref')

        # Initialisation du document
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # CSS pour les titres des colonnes
        style_title_col = workbook.add_format({
            'bold': True,
        })

        style_text_align = workbook.add_format({
            'align': 'center',
        })

        format_default = workbook.add_format({
            'bold': False,
        })

        # En-tête
        worksheet.write(0, 0, u"Société(s) :", format_default)
        company_names = ""
        for location in self.location_ids:
            if location.company_id.display_name not in company_names:
                if company_names:
                    company_names = company_names + ";"
                company_names = company_names + location.company_id.display_name
        worksheet.write(0, 1, company_names, format_default)

        date_file_create = fields.Date.context_today(self)
        worksheet.write(1, 0, u"Date de création\ndu fichier :", format_default)
        worksheet.write(1, 1, date_file_create, format_default)
        worksheet.write(2, 0, u"Date stock(s) :", format_default)
        worksheet.write(2, 1, self.date_stock, format_default)

        # Initialisation des lignes et colonnes
        row = 4
        col = 2

        col_nb = 8
        if display_client_order_ref:
            col_nb = 9

        worksheet.set_column(0, 0, 20)
        worksheet.set_column(1, 1, 40)
        worksheet.set_column(2, col_nb + len(self.location_ids), 20)

        # Titre des colonnes
        worksheet.write(row, 0, u"Référence", style_title_col)
        worksheet.write(row, 1, u"Désignation", style_title_col)
        for location in self.location_ids:
            worksheet.write(row, col, u"%s" % location.display_name, style_title_col)
            col += 1
        worksheet.write(row, col, u"Client", style_title_col)
        if display_client_order_ref:
            worksheet.write(row, col + 1, u"Client final", style_title_col)
            col += 1
        worksheet.write(row, col + 1, u"Commercial", style_title_col)
        worksheet.write(row, col + 2, u"BL", style_title_col)
        worksheet.write(row, col + 3, u"Qté en commande", style_title_col)
        worksheet.write(row, col + 4, u"BR", style_title_col)
        worksheet.write(row, col + 5, u"Qté à Réceptionner", style_title_col)
        worksheet.write(row, col + 6, u"Stock prévisionnel", style_title_col)

        # Ecriture du rapport / insertion des données
        picking_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        sale_order_obj = self.env['sale.order']
        row += 1

        # Filtre de date pour les mouvements de stock prévisionnels
        virtual_date_filter = [('create_date', '<=', self.date_stock),
                               '|', ('state', 'in', ('waiting', 'confirmed', 'assigned')),
                               '&', ('state', '=', 'done'), ('date', '>', self.date_stock)]

        products = self.product_ids
        if not products:
            domain = []
            if self.brand_ids:
                domain += [('brand_id', 'in', self.brand_ids._ids)]
            if self.categ_ids:
                domain += [('categ_id', 'in', self.categ_ids._ids)]
            if self.prix:
                domain += [('list_price', '>=', self.prix)]
            if self.active_product:
                pickings = picking_obj.search(
                    [('state', 'in', ['waiting', 'confirmed', 'partially_available', 'assigned']),
                     '|', ('location_id', 'in', self.location_ids.ids),
                          ('location_dest_id', 'in', self.location_ids.ids)])
                additionnal_products = pickings.mapped('move_lines').mapped('product_id')
                products |= self.env['product.product'].search(domain + [('id', 'in', additionnal_products._ids)])
                domain += [('qty_available', '>', 0)]
            products |= self.env['product.product'].search(domain)

        for product in products:
            worksheet.write(row, 0, product.default_code, format_default)
            worksheet.write(row, 1, product.name, format_default)

            products_virtual_in = sum(move_obj.search([('product_id', '=', product.id),
                                                       ('location_dest_id', 'in',
                                                        self.location_ids.ids)] + virtual_date_filter)
                                              .mapped('product_qty'))
            products_virtual_out = sum(move_obj.search([('product_id', '=', product.id),
                                                        ('location_id', 'in',
                                                         self.location_ids.ids)] + virtual_date_filter)
                                               .mapped('product_qty'))
            col = 2
            for location in self.location_ids:
                nb_products_in = sum(move_obj.search([('product_id', '=', product.id),
                                                      ('location_dest_id', '=', location.id),
                                                      ('state', '=', 'done'),
                                                      ('date', '<=', self.date_stock)]).mapped('product_qty'))
                nb_products_out = sum(move_obj.search([('product_id', '=', product.id),
                                                       ('location_id', '=', location.id),
                                                       ('state', '=', 'done'),
                                                       ('date', '<=', self.date_stock)]).mapped('product_qty'))
                stock_location_qty = nb_products_in - nb_products_out
                worksheet.write(row, col, stock_location_qty, style_text_align)
                col += 1

            delivery_pickings = picking_obj.search([('product_id', '=', product.id),
                                                    ('location_id', 'in', self.location_ids.ids),
                                                    ('state', 'not in', ('draft', 'cancel', 'done'))])
            delivery_names = "\n".join([picking.name or '-' for picking in delivery_pickings])
            customer_names = "\n".join([picking.partner_id.name or '-' for picking in delivery_pickings])
            final_customer_names = ""
            if display_client_order_ref:
                orders = sale_order_obj.search([('product_id', '=', product.id)])
                final_customer_names = "\n".join([order.client_order_ref for order in orders if order.client_order_ref])

            vendor_names = ""
            # Récupère les vendeurs liés aux bons de livraisons
            for picking in delivery_pickings:
                orders = sale_order_obj.search([('procurement_group_id', '=', picking.group_id.id)]) \
                    if picking.group_id else []
                vendor_names = "\n".join([order.user_id.name or '-' for order in orders])

            receipt_pickings = picking_obj.search([('product_id', '=', product.id),
                                                   ('location_dest_id', 'in', self.location_ids.ids),
                                                   ('state', 'not in', ('draft', 'cancel', 'done'))])
            receipt_names = "\n".join([picking.name or '-' for picking in receipt_pickings])

            worksheet.write(row, col, customer_names, format_default)
            col2 = col
            col3 = col
            if display_client_order_ref:
                worksheet.write(row, col + 1, final_customer_names, format_default)
                col += 1
                col3 += 1
            worksheet.write(row, col + 1, vendor_names, format_default)
            worksheet.write(row, col + 2, delivery_names, format_default)
            worksheet.write(row, col + 3, products_virtual_out, style_text_align)
            worksheet.write(row, col + 4, receipt_names, format_default)
            worksheet.write(row, col + 5, products_virtual_in, style_text_align)
            worksheet.write(row, col + 6,
                            "=%s - %s + %s" % (" + ".join([xl_rowcol_to_cell(row, c) for c in xrange(2, col2)]),
                                               xl_rowcol_to_cell(row, col3 + 3),
                                               xl_rowcol_to_cell(row, col3 + 5),
                                               ), style_text_align)
            row += 1

        worksheet.write(row+1, 0, u"Total")
        # Réinitialisation du numéro de colonne permettant le remplissage de la dernière ligne "Total"
        j = 2
        for _ in self.location_ids:
            worksheet.write(row+1, j, '=SUM(%s)' % (xl_range(5, j, row-1, j)), style_text_align)
            j += 1
        if display_client_order_ref:
            j += 1
        worksheet.write(row+1, j+3, '=SUM(%s)' % (xl_range(5, j+3, row-1, j+3)), style_text_align)
        worksheet.write(row+1, j+5, '=SUM(%s)' % (xl_range(5, j+5, row-1, j+5)), style_text_align)
        worksheet.write(row+1, j+6, '=SUM(%s)' % (xl_range(5, j+6, row-1, j+6)), style_text_align)

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()

        self.file = base64.encodestring(data)
        self.file_name = 'rapport_gestion_stock.xlsx'

        action = self.env.ref('of_sale_stock.action_of_rapport_gestion_stock').read()[0]
        action['views'] = [(self.env.ref('of_sale_stock.of_rapport_gestion_stock_view_form').id, 'form')]
        action['res_id'] = self.ids[0]
        return action
