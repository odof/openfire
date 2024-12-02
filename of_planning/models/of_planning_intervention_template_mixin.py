# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplateMixin(models.AbstractModel):
    """Abstract model for intervention template's line mixin in order to be inherited by other models to
    avoid code duplication. (e.g. of_planning.of.intervention.template` and
    `of_equipment.of.equipment.intervention.report.template`)
    """

    _name = "of.planning.intervention.template.mixin"
    _description = "Intervention template mixin"
    _order = "sequence"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=1, help="Used to order templates. Lower is better.")
    active = fields.Boolean(default=True)
    task_id = fields.Many2one(
        comodel_name="of.planning.task", string="Task", help="Task to be carried out during the intervention."
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position", string="Fiscal position", company_dependent=True
    )

    # New invoicing management
    sale_order_template_ids = fields.Many2many(
        comodel_name="sale.order.template", string="Modèles de devis disponibles"
    )
    default_sale_order_template_id = fields.Many2one(
        comodel_name="sale.order.template",
        string="Modèle de devis par défaut",
    )
    so_generation_method = fields.Selection(
        selection=[("auto", "Automatique"), ("manual", "Manuelle")],
        string="Méthode de suivi de la génération des devis",
    )
    default_sale_order_template_line_ids = fields.One2many(
        comodel_name="sale.order.template.line",
        related="default_sale_order_template_id.sale_order_template_line_ids",
        readonly=True,
    )

    # INTERVENTION REPORT (IR)
    report_use_default = fields.Boolean(
        string="Use default report (IR)", default=False, help="Use values set in the default template for the report."
    )
    report_title = fields.Char(
        string="Report title (IR)",
        translate=True,
        help="Define a title for the PDF document of the intervention report.",
    )

    # Intervention
    report_intervention = fields.Boolean(
        string="INTERVENTION (IR)", help="Selects or deselects all items to be displayed related to the intervention."
    )
    report_intervention_partner_id = fields.Boolean(
        string="Customer (IR)", help='Adds the customer to the "Intervention" section of the PDF document.'
    )
    report_intervention_partner_code = fields.Boolean(
        string="Customer code (IR)", help='Adds the customer code to the "Intervention" section of the PDF document.'
    )
    report_intervention_task_id = fields.Boolean(
        string="Task (IR)", help='Adds the task to the "Intervention" section of the PDF document.'
    )
    report_intervention_task_description = fields.Boolean(
        string="Task description (IR)",
        help='Adds the task description to the "Intervention" section of the PDF document.',
    )
    report_intervention_date = fields.Boolean(
        string="Start date (IR)", help='Adds the intervention date to the "Intervention" section of the PDF document.'
    )
    report_intervention_duration = fields.Boolean(
        string="Duration (IR)",
        help='Adds the duration of the intervention in the "Intervention" section of the PDF document.',
    )
    report_intervention_team_id = fields.Boolean(
        string="Team (IR)", help='Adds the selected team to the "Intervention" section of the PDF document.'
    )
    report_intervention_employee_ids = fields.Boolean(
        string="Operator(s) (IR)", help='Adds technicians to the "Intervention" section of the PDF document.'
    )
    report_intervention_company_id = fields.Boolean(
        string="Company (IR)", help='Adds the company to the "Intervention" section of the PDF document.'
    )
    report_intervention_label = fields.Boolean(string="Label (IR)")
    report_intervention_address = fields.Boolean(string="Address (IR)")
    report_intervention_contact = fields.Boolean(string="Contact (IR)")
    report_intervention_type = fields.Boolean(string="Intervention type (IR)")
    report_intervention_description = fields.Boolean(
        string="External description (IR)",
        help='Adds the external description to the "Intervention" section of the PDF document.',
    )
    report_intervention_internal_description = fields.Boolean(
        string="Internal description (IR)",
        help='Adds the internal description to the "Intervention" section of the PDF document.',
    )

    # Order
    report_order = fields.Boolean(
        string="ORDER (IR)",
        help="Allows you to select or deselect all the items to be displayed "
        "linked to the order associated with the intervention.",
    )
    report_order_name = fields.Boolean(
        string="Order number (IR)",
        help='Adds the associated order number to the "Order" section of the PDF document.',
    )
    report_order_confirmation_date = fields.Boolean(
        string="Confirmation date (IR)",
        help='Adds the associated order confirmation date to the "Order" section of the PDF document.',
    )
    report_order_user_id = fields.Boolean(
        string="Vendor (IR)",
        help='Adds the seller of the associated order to the "Order" section of the PDF document.',
    )
    report_order_inspection_visit_date = fields.Boolean(
        string="Inspection visit date (IR)",
        help='Adds the technical inspection date of the associated order in the "Order" section of the PDF document.',
    )
    report_order_totals = fields.Boolean(
        string="Totals (IR)", help='Adds the associated order total to the "Order" section of the PDF document.'
    )
    report_order_intervention_notes = fields.Boolean(
        string="Intervention notes (IR)",
        help='Adds the associated order notes to the "Order" section of the PDF document.',
    )

    # Produits et travaux (lignes de commande)
    report_products = fields.Boolean(string="PRODUCTS AND WORKS (IR)")

    # Deliveries
    report_pickings = fields.Boolean(
        string="DELIVERIES (IR)", help="Adds delivery notes related to the intervention to the PDF document."
    )

    # Legal notice
    report_legal = fields.Boolean(string="LEGAL NOTICE (IR)", help="Adds legal notices to the PDF document.")

    # Intervention's minutes
    report_minutes = fields.Boolean(
        string="MINUTES (IR)", help="Allows you to select or deselect all elements of the procedure report"
    )

    # Photos
    report_photos = fields.Boolean(string="PHOTOS (IR)", help="Adds photos of the operation to the PDF document.")

    # Signatures
    report_signature = fields.Boolean(
        string="SIGNATURES (IR)", help="Adds the technician's and customer's signatures to the PDF document."
    )
    report_signature_date = fields.Boolean(string="Signature date (IR)", help="Adds signature date to PDF document.")
