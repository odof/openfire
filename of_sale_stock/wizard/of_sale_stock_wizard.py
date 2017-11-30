# -*- coding: utf-8 -*-

import base64
import csv
import StringIO
import time

from odoo import api, fields, models, _
from odoo.exceptions import Warning

class OFSaleStockLivreFactureWizard(models.TransientModel):
    _name = "of_sale_stock.livre_facture_wizard"

    file = fields.Binary('File', readonly=True)
    filename = fields.Char(string='Filename', size=256, readonly=True)
    date_from = fields.Date(string=u"à partir du")#, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string=u"jusqu'au", default=lambda self: fields.Date.context_today(self))
    type = fields.Selection([
        ("livre_nonfacture", u"livré non facturé"),
        ("facture_nonlivre", u"facturé non livré"),
        ], string="Type", default="livre_nonfacture", required=True)

    @api.multi
    def button_print(self):
        self.ensure_one()
        return self.generer_tableur()  # retourne un fichier CSV

    @api.multi
    def generer_tableur(self):
        self.ensure_one()
        # We choose to implement the flat file instead of the XML
        # CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
        header = [
            u'Commande',            # 0
            u'Ligne',               # 1
            u'Type',                # 2
            u'Prix_Unitaire',       # 3
            u'Qté_Commandée',       # 4
            u'Qté_Livrée',          # 5
            u'Qté_facturée',        # 6
            ]
        if self.type == "livre_nonfacture":
            header.append(u'à_facturer')    # 7
        else:
            header.append(u'à_livrer')      # 7

        tableurfile = StringIO.StringIO()
        w = csv.writer(tableurfile, delimiter=';')
        w.writerow([s.encode("utf-8") for s in header])  # ecriture de l'entête

        rows = self._get_lines()
        for row in rows:
            listrow = list(row)
            if self.type == "livre_nonfacture":  # à facturer
                listrow.append(listrow[5] - listrow[6])
            else:  # à livrer
                listrow.append(listrow[6] - listrow[5])
            w.writerow([unicode(s).encode("utf-8") for s in listrow])

        date_to = self.date_to or fields.Date.context_today(self)
        tableurvalue = tableurfile.getvalue()
        formatted_date_from = self.date_from and self.date_from.replace('-', '') or ''
        formatted_date_to = date_to.replace('-', '')
        filename = 'Ventes-Livraisons-Facturation'
        if formatted_date_from:
            filename += '-' + formatted_date_from[6:8] + formatted_date_from[4:6] + formatted_date_from[0:4]
        filename += '-' + formatted_date_to[6:8] + formatted_date_to[4:6] + formatted_date_to[0:4]
        filename += '.csv'
        self.write({
            'file': base64.encodestring(tableurvalue),
            'filename': filename,  # 'Ventes-Livraisons-Facturation%s%s.csv' % (formatted_date_from, formatted_date_to),
            })
        tableurfile.close()

        action = {
            'name': u'Livré-Facturé',
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=of_sale_stock.livre_facture_wizard&id=" + str(self.id) + "&filename_field=filename&field=file&download=true&filename=" + self.filename,
            'target': 'self',
            }
        return action

    def _get_lines(self):#, date_from=False, date_to):
        def _query_where_clause(date_from, date_to, type):
            clause = u"""
            so.state in ('sale', 'done')
              AND sol.price_unit > 0"""
            if type == "livre_nonfacture":
                clause += u"""
                AND COALESCE(invoiced.qty_fact, 0) < COALESCE(delivered.qty_livr, 0)"""
            else:
                clause += u"""
                AND COALESCE(invoiced.qty_fact, 0) > COALESCE(delivered.qty_livr, 0)"""
            if date_from:
                clause += u"""
                  AND so.date_order >= """
                clause += u"'" + date_from + u"'"
            if date_to:
                clause += u"""
                  AND so.date_order <= """
                clause += u"'" + date_to + u"'"
            return clause

        def _invoiced_clause(date_from, date_to):
            # facturés
            clause = u"""
            SELECT rel.order_line_id, SUM(ail.quantity) AS "qty_fact"
            FROM sale_order_line_invoice_rel AS rel
            INNER JOIN account_invoice_line AS ail ON ail.id = rel.invoice_line_id
            INNER JOIN account_invoice AS ai ON ai.id = ail.invoice_id
            WHERE ai.move_name IS NOT NULL"""
            if date_from:
                clause += u"""
                  AND ai.date_invoice >= """
                clause += u"'" + date_from + u"'"
            if date_to:
                clause += u"""
                  AND ai.date_invoice <= """
                clause += u"'" + date_to + u"'"
            clause += u"""
            GROUP BY rel.order_line_id
            """
            return clause

        def _delivered_clause(date_from, date_to):
            # livrés
            clause = u"""
            SELECT sol2.id, pt.type,
                CASE WHEN pt.type IN ('consu', 'product') THEN COALESCE(SUM(sm.product_qty), 0)"""
            if date_from and date_to:  # du ... au ...
                clause += u"""
                     WHEN sol2.of_date_delivered >= """
                clause += u"'" + date_from + u"'"
                clause += u"""
                       AND sol2.of_date_delivered <= """
                clause += u"'" + date_to + u"'"
            elif date_from and not date_to:  # à partir du ...
                clause += u"""
                     WHEN sol2.of_date_delivered >= """
                clause += u"'" + date_from + u"'"
            elif not date_from and date_to:  # jusqu'au ...
                clause += u"""
                     WHEN sol2.of_date_delivered <= """
                clause += u"'" + date_to + u"'"
            else:  # jusqu'à aujourd'hui
                clause += u"""
                     WHEN sol2.of_date_delivered <= NOW()"""
            clause += u""" THEN sol2.qty_delivered
                ELSE 0 END AS "qty_livr"
            FROM sale_order_line AS sol2
            LEFT JOIN product_product AS pp ON pp.id=sol2.product_id
            LEFT JOIN product_template AS pt ON pt.id=pp.product_tmpl_id
            LEFT JOIN procurement_order AS po ON po.sale_line_id = sol2.id
            LEFT JOIN stock_move AS sm ON sm.procurement_id = po.id
                                AND sm.state = 'done'"""
            if date_from:
                clause += u"""
                                AND sm.date >= """
                clause += u"'" + date_from + u"'"
            if date_to:
                clause += u"""
                                AND sm.date <= """
                clause += u"'" + date_to + u"'"
            clause += u"""
            GROUP BY sol2.id, pt.type, sol2.qty_delivered
            """
            return clause

        query = u"""
        SELECT so.name, sol.name, delivered.type, sol.price_unit, sol.product_uom_qty, delivered.qty_livr, COALESCE(invoiced.qty_fact, 0)
            FROM sale_order AS so
            INNER JOIN sale_order_line AS sol ON sol.order_id = so.id
            LEFT JOIN (
        """
        # requète facturation
        query += _invoiced_clause(self.date_from, self.date_to)

        query += u"""
            ) AS invoiced ON invoiced.order_line_id = sol.id
            LEFT JOIN (
        """
        # requète livraison
        query += _delivered_clause(self.date_from, self.date_to)

        query += u"""
            ) AS delivered ON delivered.id = sol.id
            WHERE 
        """
        query += _query_where_clause(self.date_from, self.date_to, self.type)

        query += u"""
        ORDER BY so.id, sol.sequence, sol.id
        """

        self._cr.execute(query)
        result = self._cr.fetchall()
        return result

