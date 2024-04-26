# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if mobile_phone := args.get('mobile_phone'):
            mutation['mobile_phone'] = mobile_phone

        if work_phone := args.get('work_phone'):
            mutation['work_phone'] = work_phone

        if work_email := args.get('work_email'):
            mutation['work_email'] = work_email

        return mutation
