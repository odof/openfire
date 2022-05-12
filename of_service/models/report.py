# -*- encoding: utf-8 -*-

from odoo import api, models


class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        if report_name == 'of_planning.of_planning_fiche_intervention_report_template':
            self = self.with_context(copy_to_di=True, fiche_intervention=True)
        return super(Report, self).get_pdf(docids, report_name, html=html, data=data)
