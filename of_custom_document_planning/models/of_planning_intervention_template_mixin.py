# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplateMixin(models.AbstractModel):
    _inherit = "of.planning.intervention.template.mixin"

    # INTERVENTION REPORT (IR)
    report_order_pdf = fields.Boolean(
        string="Order (IR)",
        help="Adds the PDF of the order associated with the intervention as an appendix to the PDF document.",
    )
    report_picking_pdf = fields.Boolean(
        string="Delivery notes (IR)",
        help="Adds PDFs of delivery notes associated with the intervention as an appendix to the PDF document.",
    )
    report_invoice_pdf = fields.Boolean(
        string="Invoices (IR)", help="Adds the PDF invoice for the intervention as an appendix to the PDF document."
    )
    report_purchase_pdf = fields.Boolean(
        string="Purchases (IR)",
        help="Adds the PDF of the purchase order associated with the intervention as an appendix to the PDF document.",
    )
