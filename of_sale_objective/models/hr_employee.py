# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sale_objective = fields.Boolean(
        string="Sale objectives", help="Indique si des objectifs de ventes doivent être définis pour cet employé"
    )
