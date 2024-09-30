# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # CRM
    of_lost_opportunity_stage_id = fields.Many2one(
        comodel_name="crm.stage",
        string="(OF) Lost stage of opportunities",
        help="Allows you to indicate which stage is associated with the loss of opportunity for analysis purposese",
        config_parameter="of.sale.crm.crm.stage.lost_opportunity_stage_id",
    )

    # Sales
    of_sale_order_start_state = fields.Selection(
        selection=[
            ("estimate", 'Orders are created at the initial "Estimate" stage.'),
            ("quotation", 'Orders are created at the initial "Quotation" stage.'),
        ],
        string="(OF) Starting state of orders",
        default="quotation",
        config_parameter="of.sale.crm.sale.order.start_state",
    )
    group_of_estimate_sale_order_state = fields.Boolean(
        string="Orders will be created in the 'Estimate' stage",
        implied_group="of_sale_crm.group_of_estimate_sale_order_state",
        compute="_compute_sale_order_start_state",
        store=True,
        readonly=False,
    )
    group_of_quotation_sale_order_state = fields.Boolean(
        string="Orders will be created in the 'Quotation' stage",
        implied_group="of_sale_crm.group_of_quotation_sale_order_state",
        compute="_compute_sale_order_start_state",
        store=True,
        readonly=False,
    )

    @api.depends("of_sale_order_start_state")
    def _compute_sale_order_start_state(self):
        for settings in self:
            settings.group_of_estimate_sale_order_state = settings.of_sale_order_start_state == "estimate"
            settings.group_of_quotation_sale_order_state = settings.of_sale_order_start_state == "quotation"
