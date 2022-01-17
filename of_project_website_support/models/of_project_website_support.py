# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

    of_ticket_ids = fields.One2many(
        comodel_name='website.support.ticket', string=u"Tickets supports", compute='_compute_of_tickets')
    of_ticket_count = fields.Integer(string=u"Nombre de tickets", compute='_compute_of_tickets')

    @api.multi
    def _compute_of_tickets(self):
        for task in self:
            task.of_ticket_ids = self.env['website.support.ticket'].search([('of_task_id', '=', task.id)])
            task.of_ticket_count = len(task.of_ticket_ids)

    @api.multi
    def action_view_tickets(self):
        action = self.env.ref('website_support.website_support_ticket_action_partner').read()[0]
        if len(self._ids) == 1:
            context = {
                'default_of_task_id': self.id,
            }
            action['context'] = str(context)
        action['domain'] = [('of_task_id', 'in', self._ids)]
        action['view_mode'] = 'tree,form'
        action['views'] = [(False, u'tree'), (False, u'form')]
        return action


class WebsiteSupportTicket(models.Model):
    _inherit = 'website.support.ticket'

    of_task_id = fields.Many2one(comodel_name='project.task', string=u"Tâche associée")

    @api.multi
    def name_get(self):
        result = []
        for ticket in self:
            result.append((ticket.id, "%s - %s" % (ticket.ticket_number, ticket.subject)))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('subject', operator, name), ('ticket_number', operator, name)]
        tickets = self.search(domain + args, limit=limit)
        return tickets.name_get()
