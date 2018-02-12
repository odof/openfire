# -*- coding: utf-8 -*-
from odoo import api, fields, models
import base64
from cStringIO import StringIO
import xlsxwriter
from xlsxwriter.utility import xl_range

class SaleStockImpressionWizard(models.TransientModel):
    _name = "rapport.gestion.stock.wizard"

    product_ids = fields.Many2many('product.product', string=u"Articles")
    file = fields.Binary(string='Fichier')
    file_name = fields.Char(string='Nom du fichier', size=64, default='articles.xlsx')
    location_ids = fields.Many2many('stock.location', string="Emplacement", required=True)
    date_stock = fields.Date(string='Date stock', required=True)

    @api.multi
    def action_generate_excel_file(self):
        self.ensure_one()

        # Initialisation du document

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # CSS pour les titres des collonnes
        style_title_col = workbook.add_format({
            'bold': True,
        })

        style_text_align = workbook.add_format({
            'align': 'center',
        })

        format_default = workbook.add_format({
            'bold': False,
        })

        #En tête
        worksheet.write(0, 0, u"Société(s)  :", format_default)
        company_names = ""
        for location in self.location_ids:
            if location.company_id.display_name not in company_names:
                company_names = company_names + location.company_id.display_name + ";"
        worksheet.write(0, 1, company_names, format_default)

        date_file_create = fields.Date.context_today(self)
        worksheet.write(1, 0, u"Date de \ncréation du \nfichier:", format_default)
        worksheet.write(1, 1, date_file_create, format_default)
        worksheet.write(2, 0, u"Date stock(s):", format_default)
        worksheet.write(2, 1, self.date_stock, format_default)

        # Initialisation des lignes et colonnes
        row = 4
        col = 2
        # Titre des colonnes
        worksheet.write(row, 0, u"Référence", style_title_col)
        worksheet.write(row, 1, u"Désignation", style_title_col)
        for location in self.location_ids:
            worksheet.write(row, col, u"%s" % (location.display_name), style_title_col)
            col += 1
        worksheet.write(row, col, u"Client", style_title_col)
        worksheet.write(row, col + 1, u"Commercial", style_title_col)
        worksheet.write(row, col + 2, u"BL", style_title_col)
        worksheet.write(row, col + 3, u"Qté en commande", style_title_col)
        worksheet.write(row, col + 4, u"BR ", style_title_col)
        worksheet.write(row, col + 5, u"Qté à \nRécep", style_title_col)
        worksheet.write(row, col + 6, u"Stock \nprévi", style_title_col)

        # Ecriture du rapport / insertion des données
        picking_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        sale_order_obj = self.env['sale.order']
        row += 1

        # Filtre de date pour les mouvements de stock prévisionnels
        virtual_date_filter = [('create_date', '<=', self.date_stock),
                               '|', ('state', 'in', ('waiting', 'confirmed', 'assigned')),
                               '&', ('state', '=', 'done'), ('date', '>', self.date_stock)]

        for product in self.product_ids:
            worksheet.write(row, 0, product.default_code, format_default)
            worksheet.write(row, 1, product.name, format_default)

            products_virtual_in = move_obj.search([('product_id', '=', product.id),
                                                   ('location_dest_id', 'in', self.location_ids.ids)] + virtual_date_filter, count=True)
            products_virtual_out = move_obj.search([('product_id', '=', product.id),
                                                    ('location_id', 'in', self.location_ids.ids)] + virtual_date_filter, count=True)
            col = 2
            for location in self.location_ids:
                nb_products_in = move_obj.search([('product_id', '=', product.id),
                                                  ('location_dest_id', '=', location.id),
                                                  ('state', '=', 'done'),
                                                  ('date', '<=', self.date_stock)], count=True)
                nb_products_out = move_obj.search([('product_id', '=', product.id),
                                                   ('location_id', '=', location.id),
                                                   ('state', '=', 'done'),
                                                   ('date', '<=', self.date_stock)], count=True)
                stock_location_qty = nb_products_in - nb_products_out
                worksheet.write(row, col, stock_location_qty, style_text_align)
                col += 1

            bons_de_livraison = picking_obj.search([('product_id', '=', product.id),
                                            ('location_id', 'in', self.location_ids.ids),
                                            ('state', 'not in', ('draft', 'cancel', 'done'))])
            affichage_BL = "\n".join([bl.name +";" for bl in bons_de_livraison])
            affichage_CL = "\n".join([bl.partner_id.name + ";" for bl in bons_de_livraison])

            affichage_Commercial = ""
            # Récupère les vendeurs liés aux bons de livraisons
            for bl in bons_de_livraison:
                vendeurs = sale_order_obj.search([('procurement_group_id', '=', bl.group_id.id)]) if bl.group_id else []
                affichage_Commercial = "\n".join([vendeur.user_id.name + ";" for vendeur in vendeurs])

            affichage_BR = ""
            bons_de_reception = picking_obj.search([('product_id', '=', product.id),
                                            ('location_dest_id', 'in', self.location_ids.ids),
                                            ('state', 'not in', ('draft', 'cancel', 'done'))])
            affichage_BR = "\n".join([br.name +";" for br in bons_de_reception])

            stock_previsionnel = products_virtual_in - products_virtual_out

            worksheet.write(row, col, affichage_CL, format_default)
            worksheet.write(row, col + 1, affichage_Commercial, format_default)
            worksheet.write(row, col + 2, affichage_BL, format_default)
            worksheet.write(row, col + 3, products_virtual_out, style_text_align)
            worksheet.write(row, col + 4, affichage_BR, format_default)
            worksheet.write(row, col + 5, products_virtual_in, style_text_align)
            worksheet.write(row, col + 6, stock_previsionnel, style_text_align)
            row+=1

        worksheet.write(row+1, 0, u"Total")
        j=2 # Réinitialisation du numéro de colonne permettant le remplissage de la dernière ligne "Total"
        for item in self.location_ids:
            worksheet.write(row+1, j, '=SUM(%s)' % (xl_range(5, j, row-1, j)), style_text_align)
            j+=1
        worksheet.write(row+1, j+3, '=SUM(%s)' % (xl_range(5, j+3, row-1, j+3)), style_text_align)
        worksheet.write(row+1, j+5, '=SUM(%s)' % (xl_range(5, j+5, row-1, j+5)), style_text_align)
        worksheet.write(row+1, j+6, '=SUM(%s)' % (xl_range(5, j+6, row-1, j+6)), style_text_align)

        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()

        self.file = base64.encodestring(data)
        self.file_name = 'rapport_gestion_stock.xlsx'

        action = self.env.ref('of_sale_stock.action_of_sale_stock_report').read()[0]
        action['views'] = [(self.env.ref('of_sale_stock.of_rapport_gestion_stock_view_form').id, 'form')]
        action['res_id'] = self.ids[0]
        return action
