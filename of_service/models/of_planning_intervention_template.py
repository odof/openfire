# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = "of.planning.intervention.template"

    type_id = fields.Many2one(
        comodel_name="of.service.request.type",
        string="Type",
        required=True,
        help="The type allows you to categorize the intervention:\n"
        "* Servicing - Maintenance\n"
        "* Installation\n"
        "* AFTER-SALES SERVICE\n"
        "* Technical visit",
    )
    planning_granularity = fields.Selection(
        selection=[
            ("weekly", "Weekly"),
            ("fortnightly", "Fortnightly"),
            ("monthly", "Monthly"),
        ],
        string="Planning granularity",
        help="Granularity is used to define the reference planning period by task type. "
        "This granularity is used to calculate the end date once the start date has been entered, "
        "to calculate the end date once the start date has been entered.\nDefault:\n"
        "  * For an installation, the planning granularity is fortnightly.\n"
        "  * For an after-sales service (when the after-sales service field is filled in), the planning granularity is "
        "weekly.\n"
        "  * For maintenance (recurring operations), the planning granularity is monthly.",
    )

    @api.model
    def _name_search(self, name="", args=None, operator="ilike", limit=100):
        """Override the name_search method to filter the templates by type_id if the context contains
        of_search_by_type_id."""
        if type_id := self._context.get("of_search_by_type_id"):
            args += [("type_id", "=", type_id)]

        return super()._name_search(name, args, operator, limit)
