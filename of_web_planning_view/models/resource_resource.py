# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from random import randint

from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _default_color(self):
        return randint(1, 11)  # nosec

    color = fields.Integer(default=_default_color)
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=False,
    )
