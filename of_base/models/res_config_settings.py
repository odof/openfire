# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_display_city = fields.Boolean(
        string="(OF) Display city",
        config_parameter="of.partner.display_city",
        help="Displays the city in parentheses after the partner name when searching for a partner",
    )
    of_ref_mode = fields.Selection(related="company_id.of_ref_mode", readonly=False, string="(OF) Customer reference")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", required=True, default=lambda self: self.env.user.company_id
    )
    of_invoicing_plan = fields.Selection(
        string="(OF) Invoicing plan",
        selection=[("basic", "Basic"), ("standard", "Standard"), ("expert", "Expert"), ("advanced", "Advanced")],
        default=False,
        config_parameter="of.base.invoicing_plan",
    )
    of_base_type = fields.Selection(
        string="(OF) Type",
        selection=[
            ("customer", "Customer"),
            ("supplier", "Supplier"),
            ("customer_supplier", "Expert"),
            ("demo", "Demo"),
            ("internal_test", "Internal test"),
            ("customer_test", "Customer test"),
        ],
        default=False,
        config_parameter="of.base.base_type",
    )
    of_business_sectors_ids = fields.Many2many(
        comodel_name="of.business.sectors",
        relation="res_config_business_sector_rel",
        string="(OF) Business sectors",
        compute="_compute_of_business_sectors_ids",
        inverse="_inverse_of_business_sectors_ids",
    )
    of_business_sectors_ids_str = fields.Char(
        comodel_name="of.business.sectors",
        config_parameter="of.base.business_sectors_ids",
        string="(OF) Business sectors",
        help="Technical field to store M2M fields into a config parameter. As config_parameters does not accept m2m "
        "field, we store the fields with a comma separated string into a Char config field.",
    )

    @api.depends("of_business_sectors_ids_str")
    def _compute_of_business_sectors_ids(self):
        for setting in self:
            if setting.of_business_sectors_ids_str:
                ids = setting.of_business_sectors_ids_str.split(",")
                ids = [int(id) for id in ids if id.isdigit()]
                setting.of_business_sectors_ids = self.env["of.business.sectors"].search([("id", "in", ids)])
            else:
                setting.of_business_sectors_ids = None

    def _inverse_of_business_sectors_ids(self):
        for setting in self:
            if setting.of_business_sectors_ids:
                setting.of_business_sectors_ids_str = ",".join(
                    setting.of_business_sectors_ids.mapped(lambda x: str(x.id))
                )
            else:
                setting.of_business_sectors_ids_str = ""

    def execute(self):
        if not self.env.user._is_admin_or_superuser():
            private_fields = ["of_base_type", "of_business_sectors_ids_str", "of_invoicing_plan"]
            default_of_base_values = self.default_get(private_fields)
            if any(getattr(self, field) != default_of_base_values[field] for field in private_fields):
                raise UserError(
                    _(
                        "You have no the permission to change one of the following settings :\n"
                        "* Base > (OF) Invoicing plan\n* Base > (OF) Type\n* Base > (OF) Business sectors"
                    )
                )
        return super().execute()
