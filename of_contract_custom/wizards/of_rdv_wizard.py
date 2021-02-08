# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.addons.of_planning_tournee.wizard.rdv import OfTourneeRdv as OfTourneeRdvIn
from odoo.exceptions import UserError

@api.multi
def button_confirm(self):
    """
    Crée un RDV d'intervention puis l'ouvre en vue form.
    Crée aussi une intervention récurrente si besoin.
    """
    self.ensure_one()
    if not self._context.get('tz'):
        self = self.with_context(tz='Europe/Paris')

    intervention_obj = self.env['of.planning.intervention']
    # service_obj = self.env['of.service']

    # Vérifier que la date de début et la date de fin sont dans les créneaux
    employee = self.employee_id
    if not employee.of_segment_ids:
        raise UserError("Il faut configurer l'horaire de travail de tous les intervenants.")

    # date_propos_dt = fields.Datetime.from_string(self.date_propos)  # datetime utc proposition de rdv

    values = self.get_values_intervention_create()

    res = intervention_obj.create(values)

    # Creation/mise à jour du service si creer_recurrence
    if self.date_next:
        if self.service_id:
            self.service_id.write({
                'date_next': self.date_next,
                'date_fin': self.date_fin_planif
            })

    return {
        'type': 'ir.actions.act_window',
        'res_model': 'of.planning.intervention',
        'view_type': 'form',
        'view_mode': 'form',
        'res_id': res.id,
        'target': 'current',
        'context': self._context
    }


OfTourneeRdvIn.button_confirm = button_confirm


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
