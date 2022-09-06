# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_project_ids = fields.One2many('project.project', 'of_sale_id', string="Projets")
    of_project_count = fields.Integer(string="Nb. projets", compute="_compute_of_project_count")

    @api.depends('of_project_ids')
    def _compute_of_project_count(self):
        for order in self:
            order.of_project_count = len(order.of_project_ids)

    def _prepare_project_vals(self):
        vals = super(SaleOrder, self)._prepare_project_vals()
        vals['of_sale_id'] = self.id
        vals['partner_id'] = self.partner_id.id
        return vals

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
            action['context'] = {
                'default_of_sale_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        return action
