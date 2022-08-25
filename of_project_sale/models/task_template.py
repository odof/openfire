# -*- coding: utf8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class ProjectTask(models.Model):
    _inherit = 'project.task'

    of_planning_tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche du RDV")

    @api.multi
    def action_view_interventions(self):
        res = super(ProjectTask, self).action_view_interventions()
        if len(self._ids) == 1 and self.of_planning_tache_id:
            context = safe_eval(res['context'])
            context.update({
                'default_tache_id': self.of_planning_tache_id.id,
            })
            res['context'] = context
        return res


class OFProjectTaskTemplate(models.Model):
    _name = 'of.project.task.template'
    _description = u"Modèle de tâches"

    name = fields.Char(string=u"Nom", required=True)
    duration = fields.Float(string=u"Durée", digits=(6, 2))
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string=u"Article", index=True)
    planning_tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche du RDV")
    user_id = fields.Many2one(comodel_name='res.users', string=u"Assigné à")
