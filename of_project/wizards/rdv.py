# -*- coding: utf8 -*-

from odoo import models, fields, api


class OFTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche", index=True)

    @api.model
    def default_get(self, fields=None):
        res = super(OFTourneeRdv, self).default_get(fields)
        task_obj = self.env['project.task']
        active_model = self._context.get('active_model', '')
        if active_model == 'project.task':
            task_id = self._context['active_ids'][0]
            task = task_obj.browse(task_id)
            partner = task.partner_id
            res['partner_id'] = partner and partner.id or False
            res['partner_address_id'] = partner and partner.id or False
            res['task_id'] = task and task.id or False
            res['duree'] = task and task.planned_hours
            res['pre_employee_ids'] = task.user_id and [task.user_id.id] or False

        return res

    @api.multi
    def get_values_intervention_create(self):
        """
        :return: dictionnaires de valeurs pour la création du RDV Tech
        """
        res = super(OFTourneeRdv, self).get_values_intervention_create()
        if self.task_id:
            res['task_id'] = self.task_id.id

        return res
