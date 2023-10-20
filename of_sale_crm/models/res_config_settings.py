# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # CRM
    group_estimation_sale_order_state = fields.Boolean(
        string="Orders created in the Estimate stage",
        implied_group='of_sale_crm.group_estimatate_sale_order_state',
        group='base.group_portal,base.group_user,base.group_public',
    )
    group_quotation_sale_order_state = fields.Boolean(
        string="Orders created in the Quotation stage",
        implied_group='of_sale_crm.group_quotation_sale_order_state',
        group='base.group_user',
    )
    of_lost_opportunity_stage_id = fields.Many2one(
        comodel_name='crm.stage',
        string="(OF) Lost stage of opportunities",
        help="Allows you to indicate which stage is associated with the loss of opportunity for analysis purposese",
        config_parameter='of.sale.crm.crm.stage.lost_opportunity_stage_id',
    )

    # Sales
    of_sale_order_start_state = fields.Selection(
        selection=[
            ('estimate', "Orders are created at the initial \"Estimate\" stage."),
            ('quotation', "Orders are created at the initial \"Quotation\" stage."),
        ],
        string="(OF) Starting state of orders",
        default='quotation',
        config_parameter='of.sale.crm.sale.order.start_state',
    )
