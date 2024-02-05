# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFOutlayAnalysisKanbanRecord(models.Model):
    _inherit = 'of.outlay.analysis.kanban.record'

    @api.model
    def recompute_records(self, analysis):
        super(OFOutlayAnalysisKanbanRecord, self).recompute_records(analysis)
        lang = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'fr_FR'))])
        kanban_records = self.search(
            [('analysis_id', '=', analysis.id),
             ('type', '=', '02_expense'),
             ('category', 'in', ('01_initial', '02_complementary'))]
        )
        sale_lines = analysis.filter_section(
            analysis.sale_line_ids.filtered('of_outlay_analysis_cost_selected').filtered('of_subcontracted_service')
        )
        kanban_records[0].write({
            'label4': u"Dont sous-traitance :",
            'value4': self.format_number(
                sum(sale_lines.filtered(lambda line: line.of_outlay_analysis_type == 'init')
                    .mapped(lambda line: line.purchase_price * line.product_uom_qty)),
                lang, currency=analysis.currency_id),
        })
        kanban_records[1].write({
            'label4': u"Dont sous-traitance :",
            'value4': self.format_number(
                sum(sale_lines.filtered(lambda line: line.of_outlay_analysis_type == 'compl')
                    .mapped(lambda line: line.purchase_price * line.product_uom_qty)),
                lang, currency=analysis.currency_id),
        })
