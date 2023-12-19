# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    planning_color = fields.Integer(
        string="Planning color",
        help="Color used to display the intervention in the planning view",
    )
