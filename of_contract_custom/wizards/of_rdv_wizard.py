# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    @api.model
    def default_get(self, fields=None):
        res = super(OfTourneeRdv, self).default_get(fields)
        service_obj = self.env['of.service']
        active_model = self._context.get('active_model', '')
        if active_model == 'of.service':
            service_id = self._context['active_ids'][0]
            service = service_obj.browse(service_id)
            res['pre_employee_ids'] = [(6, 0, [emp.id for emp in service.employee_ids])]
        return res

    @api.multi
    def get_values_intervention_create(self):
        vals = super(OfTourneeRdv, self).get_values_intervention_create()
        if self.service_id and self.service_id.contract_line_id:
            vals.update({
                'contract_line_id' : self.service_id.contract_line_id.id
            })
        return vals
