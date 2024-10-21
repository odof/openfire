# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFEquipmentInterventionReportTemplateLine(models.Model):
    _name = "of.equipment.intervention.report.template.line"
    _inherit = "of.planning.intervention.line.mixin"
    _description = "Intervention template's line"

    template_id = fields.Many2one(comodel_name="of.equipment.intervention.report.template")
