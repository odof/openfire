# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFFollowupConfirmNextStep(models.TransientModel):
    _name = 'of.followup.confirm.next.step'
    _description = "Assistant de validation de passage à l'étape suivante"

    task_id = fields.Many2one(comodel_name='of.followup.task', string=u"Tâche de suivi")

    @api.model
    def default_get(self, fields):
        result = super(OFFollowupConfirmNextStep, self).default_get(fields)
        if self._context.get('active_model') == 'of.followup.task' and self._context.get('active_id'):
            result['task_id'] = self._context.get('active_id')
        return result

    @api.multi
    def validate(self):
        self.ensure_one()
        # On cherche l'étape suivante
        state = self.env['of.followup.task.type.state'].search(
            [('task_type_id', '=', self.task_id.type_id.id),
             ('sequence', '>', self.task_id.predefined_state_id.sequence)],
            limit=1)
        if state:
            self.task_id.write({'force_state': True,
                                'state_id': state.id})
        return True
