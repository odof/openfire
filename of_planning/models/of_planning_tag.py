# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningTag(models.Model):
    _name = "of.planning.tag"
    _description = "Intervention tag"
    _order = "sequence"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(help="Used to order tags. Lower is better.", default=1)
    active = fields.Boolean(default=True, help="Hides the label without deleting it.")
    color = fields.Integer(string="Color index")
    intervention_ids = fields.Many2many(
        comodel_name="calendar.event", column1="tag_id", column2="intervention_id", string="Interventions"
    )
