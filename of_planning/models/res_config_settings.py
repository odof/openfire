# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_hide_remaining_balance = fields.Boolean(
        string="(OF) Hide remaining balance", related="company_id.of_hide_remaining_balance", readonly=False
    )
    of_company_choice = fields.Selection(
        string="(OF) Company choice for interventions", related="company_id.of_company_choice", readonly=False
    )
    of_automatic_sectors = fields.Boolean(
        string="(OF) Auto. Sectors assignation", related="company_id.of_automatic_sectors", readonly=False
    )
    group_intervention_use_deliveries = fields.Boolean(
        string="(OF) Intervention's pickings", implied_group="of_planning.group_intervention_use_deliveries"
    )
    of_default_intervention_template_id = fields.Many2one(
        comodel_name="of.planning.intervention.template",
        related="company_id.of_default_intervention_template_id",
        readonly=False,
        string="(OF) Default Intervention template",
    )
    of_is_intervention_template_required = fields.Boolean(
        related="company_id.of_is_intervention_template_required",
        readonly=False,
        string="(OF) Make the Intervention template mandatory",
    )
