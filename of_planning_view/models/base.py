# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.osv import expression


class Base(models.AbstractModel):
    _inherit = 'base'

    def _planning_add_empty_records_domain(self, resource_ids, field_id):
        domain = super()._planning_add_empty_records_domain(resource_ids, field_id)
        if field_id.relation == 'resource.resource':
            domain = expression.AND(
                [
                    domain,
                    [
                        '|',
                        ('employee_id.of_is_operator', '=', 'True'),
                        ('employee_id.of_is_salesperson', '=', 'True'),
                    ],
                ]
            )
        return domain
