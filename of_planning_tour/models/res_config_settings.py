# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

SELECTION_SEARCH_TYPES = [
    ("distance", "Distance (km)"),
    ("duration", "Duration (min)"),
]

SELECTION_SEARCH_MODES = [
    ("oneway", "One way"),
    ("return", "Return"),
    ("round_trip", "Round trip"),
    ("oneway_or_return", "One way or Return"),
    ("oneway_am_return_pm", "One way if morning / Return if afternoon"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    search_mode = fields.Selection(
        string="(OF) Search mode",
        selection=SELECTION_SEARCH_MODES,
        required=True,
        default="oneway_or_return",
        config_parameter="of.planning.tour.search_mode",
    )
    search_type = fields.Selection(
        string="(OF) Search type",
        selection=SELECTION_SEARCH_TYPES,
        required=True,
        default="duration",
        config_parameter="of.planning.tour.search_type",
    )
    planning_default_intervention_template_id = fields.Many2one(
        comodel_name="of.planning.intervention.template",
        string="(OF) Default intervention template for searching",
        help="Default intervention template to use when creating for an appointment.",
        config_parameter="of.planning.tour.default_planning_intervention_template_id",
    )

    # Tour planning
    nbr_months_tour_creation = fields.Integer(
        string="(OF) Tours // Create Tours over __ months",
        default=18,
        required=True,
        help="Defines the number of months on which to create the routes for each employee whose work hours "
        "are defined. Maximum: 36 months. Tip: this number must be at least equal to the maximum number "
        "of months over which you realize slots research.",
        config_parameter="of.planning.tour.nbr_months_tour_creation",
    )
    # Non modifiable pour le moment, il faudra le rendre modifiable à terme et
    # donc gérer le re-calcul des créneaux dispo
    tour_minimum_free_slot_duration = fields.Float(
        string="(OF) Tours // Minimum free slot duration",
        config_parameter="of.planning.tour.tour_minimum_free_slot_duration",
        default=0.25,
        help="Defines the minimum free slot duration in hours. It corresponds to the minimum duration between two "
        "interventions to consider that employees available.",
    )

    @api.constrains("nbr_months_tour_creation")
    def _check_nbr_months_tour_creation(self):
        for setting in self:
            if setting.nbr_months_tour_creation <= 0 or setting.nbr_months_tour_creation > 36:
                raise ValidationError(
                    _("The number of months for the tours creation must be positive and can't exceed 36.")
                )
