# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def write(self, vals):
        res = super().write(vals)

        domain_employee = [
            '|',
            '|',
            ('of_employee_ids', 'in', self.id),
            ('of_employee_id', '=', self.id),
            ('of_gb_employee_id', '=', self.id),
        ]
        self.env['calendar.event'].action_update_date(domain_employee)

        return res

    def unlink(self):
        domain_employee = [
            '|',
            '|',
            ('of_employee_ids', 'in', self.id),
            ('of_employee_id', '=', self.id),
            ('of_gb_employee_id', '=', self.id),
        ]
        self.env['calendar.event'].action_update_date(domain_employee)

        return super().unlink()
