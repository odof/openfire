# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    # -- Intervention Sheet - Joined Documents
    sheet_order_pdf = fields.Boolean(string="Order")
    sheet_picking_pdf = fields.Boolean(string="Delivery notes")
    sheet_invoice_pdf = fields.Boolean(string="Invoices")
    sheet_custom_document_ids = fields.Many2many(
        comodel_name='of.custom.document', relation='sheet_intervention_custom_document', string="Joined documents"
    )

    # -- Intervention Report - Joint Documents
    report_order_pdf = fields.Boolean(string="Order")
    report_picking_pdf = fields.Boolean(string="Delivery notes")
    report_invoice_pdf = fields.Boolean(string="Invoices")
    report_custom_document_ids = fields.Many2many(
        comodel_name='of.custom.document', relation='report_intervention_custom_document', string="Joined documents"
    )
