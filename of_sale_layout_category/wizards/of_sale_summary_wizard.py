# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleSummaryWizard(models.TransientModel):
    _name = 'of.sale.summary.wizard'
    _description = "Sale Summary Wizard"

    sale_id = fields.Many2one(comodel_name='sale.order', string="Sale Order")
    doc = fields.Html(compute='_compute_doc')

    def _compute_doc(self):
        for record in self:
            record.doc = self.env['ir.qweb']._render(
                template="of_sale_layout_category.report_sale_summary", values={'sale_id': record.sale_id}
            )
