# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


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
    of_is_closed = fields.Boolean(string=u"Ticket clôturé", compute='_compute_of_is_closed', store=True)

    @api.depends('state')
    def _compute_of_is_closed(self):
        customer_closed = self.env['ir.model.data'].get_object(
            'website_support', 'website_ticket_state_customer_closed')
        staff_closed = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_staff_closed')

        for ticket in self:
            if ticket.state in (customer_closed, staff_closed):
                ticket.of_is_closed = True
            else:
                ticket.of_is_closed = False

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

    @api.multi
    def send_ar(self):
        self.ensure_one()
        template = self.env['mail.template'].search([('name', '=', 'AR Ticket Support')])
        if not template:
            raise UserError(u"Aucun modèle de mail \"AR Ticket Support\" n'a été trouvé !")
        values = template.generate_email(self.id)
        send_mail = self.env['mail.mail'].create(values)
        send_mail.send(True)


class WebsiteSupportTicketCompose(models.Model):
    _inherit = 'website.support.ticket.compose'

    attachment_ids = fields.Many2many(comodel_name='ir.attachment', string=u"Pièces jointes")

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            values = self.env['mail.compose.message'].generate_email_for_composer(
                self.template_id.id, [self.ticket_id.id])[self.ticket_id.id]
            self.body = values['body']
            if 'attachment_ids' in values:
                self.attachment_ids = values['attachment_ids']

    @api.multi
    def send_reply(self):
        self.ensure_one()

        # Send email
        setting_staff_reply_email_template_id = self.env['ir.values'].get_default(
            'website.support.settings', 'staff_reply_email_template_id')

        if setting_staff_reply_email_template_id:
            email_wrapper = self.env['mail.template'].browse(setting_staff_reply_email_template_id)
        else:
            # Defaults to staff reply template for back compatablity
            email_wrapper = self.env['ir.model.data'].get_object('website_support', 'support_ticket_reply_wrapper')

        values = email_wrapper.generate_email([self.id])[self.id]
        values['model'] = "website.support.ticket"
        values['res_id'] = self.ticket_id.id
        values['attachment_ids'] = [(6, 0, self.attachment_ids.ids)]
        send_mail = self.env['mail.mail'].create(values)
        send_mail.send()

        # Add to message history field for back compatablity
        self.env['website.support.ticket.message'].create(
            {'ticket_id': self.ticket_id.id,
             'by': 'staff',
             'content': self.body.replace("<p>", "").replace("</p>", "")})

        if self.approval:
            # Change the ticket state to awaiting approval
            awaiting_approval_state = self.env['ir.model.data'].get_object('website_support',
                                                                           'website_ticket_state_awaiting_approval')
            self.ticket_id.state = awaiting_approval_state.id

            # Also change the approval
            awaiting_approval = self.env['ir.model.data'].get_object('website_support', 'awaiting_approval')
            self.ticket_id.approval_id = awaiting_approval.id
        else:
            # Change the ticket state to staff replied
            staff_replied = self.env['ir.model.data'].get_object('website_support',
                                                                 'website_ticket_state_staff_replied')
            self.ticket_id.state = staff_replied.id
