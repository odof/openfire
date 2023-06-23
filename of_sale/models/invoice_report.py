# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# TODO: Migrate me when `of_account_invoice_report` module will be migrated
# from odoo import models


# class OFInvoiceReportTotalGroup(models.Model):
#     _inherit = 'of.invoice.report.total.group'
#     _description = "Impression des totaux de factures et commandes de vente"

#     def filter_lines(self, lines, invoices=None):
#         self.ensure_one()
#         if not self.is_group_paiements():
#             return super().filter_lines(lines, invoices=invoices)
#         # Retour des lignes dont l'article correspond à un groupe de rapport de facture
#         #   et dont la ligne de commande associée a une date antérieure
#         #   (seul un paiement d'une facture antérieure doit figurer sur une facture)
#         if lines._name == 'account.move.line':
#             allowed_order_lines = invoices.mapped('invoice_line_ids').mapped('sale_line_ids')
#             lines = lines.filtered(
#                 lambda line: (
#                     (line.product_id in self.product_ids or line.product_id.categ_id in self.categ_ids)
#                     and line.sale_line_ids
#                     and line.sale_line_ids in allowed_order_lines
#                 )
#             )
#             # Si une facture d'acompte possède plusieurs lignes, il est impératif de les gérer de la même façon
#             invoices = lines.mapped('move_id')
#             sale_lines = lines.mapped('sale_line_ids')
#             for sale_line in sale_lines:
#                 sale_line_invoices = sale_line.invoice_lines.mapped('move_id')
#                 for sale_line2 in sale_line.order_id.order_line:
#                     if sale_line2 != sale_line and sale_line2.invoice_lines.mapped('move_id') == sale_line_invoices:
#                         lines |= sale_line2.invoice_lines.filtered(lambda line: line.invoice_id in invoices)
#             return lines
#         else:
#             return lines.filtered(
#                 lambda line: (line.product_id in self.product_ids or line.product_id.categ_id in self.categ_ids)
#             )
# End of TODO: Migrate me when `of_account_invoice_report` module will be migrated
