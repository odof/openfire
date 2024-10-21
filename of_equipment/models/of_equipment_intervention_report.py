# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFEquipmentInterventionReport(models.Model):
    _name = "of.equipment.intervention.report"
    _description = "Equipment Intervention Report"

    task_id = fields.Many2one(comodel_name="of.planning.task", string="Task")
