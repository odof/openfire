# -*- coding: utf8 -*-

from odoo import models, fields, api


class OFTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    @api.model
    def default_get(self, fields=None):
        res = super(OFTourneeRdv, self).default_get(fields)
        task_obj = self.env['project.task']
        active_model = self._context.get('active_model', '')
        if active_model == 'project.task':
            task_id = self._context['active_ids'][0]
            task = task_obj.browse(task_id)
            res['tache_id'] = task and task.of_planning_tache_id.id

        return res
