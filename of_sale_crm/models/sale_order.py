# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

AVAILABLE_PRIORITIES = [
    ("0", "Normal"),
    ("1", "Low"),
    ("2", "High"),
    ("3", "Very High"),
]


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "of.crm.stage.auto.update"]

    @api.model
    def _get_default_state(self):
        order_start_state = self.env["ir.config_parameter"].sudo().get_param("of.sale.crm.sale.order.start_state")
        return "sent" if order_start_state == "quotation" else "draft"

    of_referred_id = fields.Many2one(
        comodel_name="res.partner", string="Brought by", help="Name of business contributor", copy=False
    )
    opportunity_id = fields.Many2one(
        comodel_name="crm.lead", string="Opportunity", domain="[('type', '=', 'opportunity')]", copy=False
    )
    campaign_id = fields.Many2one(
        comodel_name="utm.campaign",
        string="Campaign",
        copy=False,
        help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, "
        "Christmas_Special",
    )
    source_id = fields.Many2one(
        comodel_name="utm.source",
        string="Source",
        copy=False,
        help="This is the source of the link Ex:Search Engine, another domain,or name of email list",
    )
    medium_id = fields.Many2one(
        comodel_name="utm.medium",
        string="Medium",
        copy=False,
        help="This is the method of delivery.Ex: Postcard, Email, or Banner Ad",
    )
    state = fields.Selection(  # override selection values
        selection=[
            ("draft", "Estimate"),
            ("sent", "Quotation"),
            ("sale", "Sale Order"),
            ("done", "Locked"),
            ("cancel", "Canceled"),
        ],
        default=_get_default_state,
    )
    of_sent_quotation = fields.Boolean(string="Quotation sent", copy=False, tracking=True)
    of_canvasser_id = fields.Many2one(comodel_name="res.users", string="Canvasser")

    # Follow-up fields
    of_sale_followup_tag_ids = fields.Many2many(
        comodel_name="of.sale.followup.tag",
        relation="sale_order_followup_tag_rel",
        column1="order_id",
        column2="tag_id",
        string="Follow-up tags",
    )
    of_priority = fields.Selection(selection=AVAILABLE_PRIORITIES, string="Priority", index=True, default="0")
    of_notes = fields.Text(string="Follow-up notes")
    of_info = fields.Text(string="Info")
    of_reference_laying_date = fields.Date(
        string="Reference laying date", compute="_compute_of_reference_laying_data", store=True
    )
    of_force_laying_date = fields.Boolean(string="Force laying date")
    of_manual_laying_date = fields.Date(string="Manual laying date")
    of_laying_week = fields.Char(string="Laying week", compute="_compute_of_reference_laying_data", store=True)
    of_main_product_brand_id = fields.Many2one(
        comodel_name="of.product.brand",
        string="Brand of the main product",
    )

    # UX fields
    of_show_update_salesman = fields.Boolean(store=False, string="Has opportunity changed")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends(
        "of_force_laying_date",
        "of_manual_laying_date",
    )
    def _compute_of_reference_laying_data(self):
        for order in self:
            laying_date = False
            if order.of_force_laying_date:
                laying_date = order.of_manual_laying_date

            order.of_reference_laying_date = laying_date
            if laying_date:
                date_laying_week = laying_date
                laying_week = laying_date.isocalendar()[1]
                order.of_laying_week = _("%(year)s - W%(week)02d", year=date_laying_week.year, week=laying_week)
            else:
                order.of_laying_week = _("Not scheduled")

    # -------------------------------------------------------------------------
    # Onchange methods
    # -------------------------------------------------------------------------

    @api.onchange("opportunity_id")
    def _onchange_opportunity_id(self):
        for order in self:
            if order.opportunity_id:
                order.user_id = order.opportunity_id.user_id
                order.of_canvasser_id = order.opportunity_id.of_canvasser_id
                order.of_show_update_salesman = True
            else:
                order._compute_user_id()

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        order_start_state = self.env["ir.config_parameter"].sudo().get_param("of.sale.crm.sale.order.start_state")
        for vals in vals_list:
            if "state" not in vals:
                if order_start_state == "estimate":
                    vals["state"] = "draft"
                elif order_start_state == "quotation" and vals.get("state", "draft") == "draft":
                    vals["state"] = "sent"
        return super().create(vals_list)

    def copy_data(self, default=None):
        """By default, the opportunity is copied when the sale order is copied (attribute copy=True)."""
        data_list = super().copy_data(default)
        for order, data in zip(self, data_list):
            if self.env["ir.config_parameter"].sudo().get_param("of.sale.of_copy_opportunity_with_sale_order"):
                data["opportunity_id"] = order.opportunity_id.id
            else:
                data["opportunity_id"] = False
        return data_list

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, **kwargs):
        result = super().message_post(**kwargs)
        if self.env.context.get("of_mark_so_as_sent"):
            self.filtered(lambda o: not o.of_sent_quotation).write({"of_sent_quotation": True})
        return result

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_confirm_estimate(self):
        for order in self:
            if order.state == "draft":
                order.state = "sent"

    def action_quotation_send(self):
        """Opens a wizard to compose an email, with relevant mail template loaded by default"""
        self.ensure_one()
        action = super().action_quotation_send()
        action["context"].update({"of_mark_so_as_sent": True})
        action["context"].pop("mark_so_as_sent")  # disable the standard behavior
        return action
