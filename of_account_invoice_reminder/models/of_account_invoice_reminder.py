# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_reminder_stage_id = fields.Many2one(
        comodel_name='of.account.invoice.reminder.stage', string=u"Niveau de relance")
    of_reminder_state = fields.Selection(
        selection=[('to_do', u"À faire"), ('done', u"OK")], string=u"État de la relance")
    of_last_reminder_sent_date = fields.Date(string=u"Date d'envoi de la dernière relance")

    @api.onchange('of_reminder_stage_id')
    def _onchange_of_reminder_stage_id(self):
        if self.of_reminder_stage_id:
            self.of_reminder_state = 'to_do'
        else:
            self.of_reminder_state = False

    @api.model
    def manage_reminder(self):
        today = fields.Date.from_string(fields.Date.today())
        for reminder_stage in self.env['of.account.invoice.reminder.stage'].search([]):
            if reminder_stage.trigger_date == 'deadline':
                for invoice in self.search([('state', '=', 'open'), ('type', '=', 'out_invoice'),
                                            ('date_due', '!=', False), ('of_reminder_stage_id', '=', False)]):
                    if (today - fields.Date.from_string(invoice.date_due)).days >= \
                            reminder_stage.trigger_delay:
                        invoice.write({'of_reminder_stage_id': reminder_stage.id,
                                       'of_reminder_state': 'to_do'})
            elif reminder_stage.trigger_date == 'invoice':
                for invoice in self.search([('state', '=', 'open'), ('type', '=', 'out_invoice'),
                                            ('date_invoice', '!=', False), ('of_reminder_stage_id', '=', False)]):
                    if (today - fields.Date.from_string(invoice.date_invoice)).days >= \
                            reminder_stage.trigger_delay:
                        invoice.write({'of_reminder_stage_id': reminder_stage.id,
                                       'of_reminder_state': 'to_do'})
            elif reminder_stage.trigger_date == 'previous_reminder':
                previous_stages = self.env['of.account.invoice.reminder.stage'].\
                    search([('sequence', '<', reminder_stage.sequence)])
                for invoice in self.search(
                        [('state', '=', 'open'), ('type', '=', 'out_invoice'),
                         ('of_reminder_stage_id', 'in', previous_stages.ids), ('of_reminder_state', '=', 'done'),
                         ('of_last_reminder_sent_date', '!=', False)]):
                    if (today - fields.Date.from_string(invoice.of_last_reminder_sent_date)).days >= \
                            reminder_stage.trigger_delay:
                        invoice.write({'of_reminder_stage_id': reminder_stage.id,
                                       'of_reminder_state': 'to_do'})

    @api.multi
    def action_send_reminder(self):
        self.ensure_one()
        if self.of_reminder_state != 'to_do':
            raise UserError(u"La facture ne doit pas être relancée !")
        if not self.partner_id.email:
            raise UserError(u"Le client de la facture n'a pas d'email !")
        wizard = self.env['of.account.invoice.reminder.send'].create({'invoice_ids': [(4, self.id)]})
        wizard.button_send_reminder()
        return True

    @api.multi
    def write(self, vals):
        if vals.get('of_reminder_state', False) == 'done':
            # Lorsqu'une relance est envoyée, on met à jour la date de dernier envoi
            vals['of_last_reminder_sent_date'] = fields.Date.today()
        return super(AccountInvoice, self).write(vals)


class OFAccountInvoiceReminderStage(models.Model):
    _name = 'of.account.invoice.reminder.stage'
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence", required=True)
    trigger_date = fields.Selection(
        selection=[('deadline', u"Après l'échéance de la facture"),
                   ('invoice', u"Après la date de facturation"),
                   ('previous_reminder', u"Après la relance précédente")], string=u"Date de déclenchement",
        required=True)
    trigger_delay = fields.Integer(string=u"Nombre de jours après la date de déclenchement")
    email_template_id = fields.Many2one(
        comodel_name='mail.template', string=u"Modèle d'email", domain="[('model', '=', 'account.invoice')]",
        required=True)

    _sql_constraints = [
        ('sequence_uniq', 'unique (sequence)', u"La séquence doit être unique !")
    ]
