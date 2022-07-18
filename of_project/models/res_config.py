# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProjectConfiguration(models.TransientModel):
    _inherit = 'project.config.settings'

    of_kanban_group = fields.Selection(
        [('none', "Aucun"), ('of_stage_id', u"Étapes assignées manuellement"), ('of_state', u"État calculé")],
        string="Regroupement Kanban des projets", required=True
    )
    group_of_planning_project = fields.Boolean(
        string=u"(OF) Planification d’intervention",
        implied_group='of_project.group_of_planning_project',
        help=u"Activer la planification d’interventions dans la tâche")
    module_of_project_sale = fields.Boolean(
        string=u"(OF) Création automatique", help="Créer un projet à la validation d’une commande")

    @api.model
    def get_default_of_kanban_group(self, fields):
        if self.env.ref('of_project.of_project_project_kanban_view_gb_stage_id').active:
            of_kanban_group = 'of_stage_id'
        elif self.env.ref('of_project.of_project_project_kanban_view_gb_state').active:
            of_kanban_group = 'of_state'
        else:
            of_kanban_group = 'none'
        return {'of_kanban_group': of_kanban_group}

    @api.multi
    def set_default_of_kanban_group(self):
        self.env.ref('of_project.of_project_project_kanban_view_gb_stage_id').active =\
            self.of_kanban_group == 'of_stage_id'
        self.env.ref('of_project.of_project_project_kanban_view_gb_state').active = self.of_kanban_group == 'of_state'
