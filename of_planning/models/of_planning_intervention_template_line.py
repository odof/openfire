# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplateLine(models.Model):
    _name = "of.planning.intervention.template.line"
    _inherit = "of.planning.intervention.line.mixin"
    _description = "Intervention template's line"

    template_id = fields.Many2one(comodel_name="of.planning.intervention.template")
