# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_project_ids = fields.One2many('project.project', 'partner_id', string="Projets")
    of_project_count = fields.Integer(string="Nb. projets", compute="_compute_of_project_count")

    @api.depends('of_project_ids')
    def _compute_of_project_count(self):
        for partner in self:
            partner.of_project_count = len(partner.of_project_ids)

    def of_action_view_project(self):
        projects = self.mapped('of_project_ids')
        action = self.env.ref('project.open_view_project_all_config').read()[0]
        if len(projects) > 1:
            action['domain'] = [('id', 'in', projects.ids)]
        elif projects:
            action['views'] = [(self.env.ref('project.edit_project').id, 'form')]
            action['res_id'] = projects.id
        else:
            action = self.env.ref('project.open_create_project').read()[0]
            action['context'] = {'default_partner_id': self.id}
        return action
