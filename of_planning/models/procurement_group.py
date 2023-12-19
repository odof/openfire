# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    of_intervention_id = fields.Many2one(comodel_name='calendar.event', string="Intervention", readonly=True)
