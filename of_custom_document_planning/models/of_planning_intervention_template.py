# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    # -- Intervention Sheet - Joined Documents
    sheet_order_pdf = fields.Boolean(
        string="Order",
        help="Adds the PDF of the order associated with the intervention as an appendix to the PDF document.",
    )
    sheet_picking_pdf = fields.Boolean(
        string="Delivery notes",
        help="Adds PDFs of delivery notes associated with the intervention as an appendix to the PDF document.",
    )
    sheet_invoice_pdf = fields.Boolean(
        string="Invoices", help="Adds the PDF invoice for the intervention as an appendix to the PDF document."
    )
    sheet_purchase_pdf = fields.Boolean(
        string="Purchases",
        help="Adds the PDF of the purchase order associated with the intervention as an appendix to the PDF document.",
    )
    sheet_custom_document_ids = fields.Many2many(
        comodel_name='of.custom.document',
        relation='sheet_intervention_custom_document',
        string="Joined documents",
        help="Adds customized documents selected in the intervention as an appendix to the PDF document.",
    )

    # -- Intervention Report - Joint Documents
    report_order_pdf = fields.Boolean(
        string="Order",
        help="Adds the PDF of the order associated with the intervention as an appendix to the PDF document.",
    )
    report_picking_pdf = fields.Boolean(
        string="Delivery notes",
        help="Adds PDFs of delivery notes associated with the intervention as an appendix to the PDF document.",
    )
    report_invoice_pdf = fields.Boolean(
        string="Invoices", help="Adds the PDF invoice for the intervention as an appendix to the PDF document."
    )
    report_purchase_pdf = fields.Boolean(
        string="Purchases",
        help="Adds the PDF of the purchase order associated with the intervention as an appendix to the PDF document.",
    )
    report_custom_document_ids = fields.Many2many(
        comodel_name='of.custom.document',
        relation='report_intervention_custom_document',
        string="Joined documents",
        help="Adds customized documents selected in the intervention as an appendix to the PDF document.",
    )
