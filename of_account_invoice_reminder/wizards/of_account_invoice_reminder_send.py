# -*- coding: utf-8 -*-

from odoo import api, fields, models
import base64


class OFAccountInvoiceReminderSend(models.TransientModel):
    _name = 'of.account.invoice.reminder.send'

    @api.model
    def default_get(self, fields):
        result = super(OFAccountInvoiceReminderSend, self).default_get(fields)
        if self._context.get('active_model') == 'account.invoice' and self._context.get('active_ids'):
            invoices = self.env['account.invoice'].browse(self._context.get('active_ids'))

            no_remind_invoices = invoices.filtered(lambda inv: inv.state != 'open' or inv.type != 'out_invoice'
                                                   or inv.of_reminder_state != 'to_do')
            invoices -= no_remind_invoices
            no_email_invoices = invoices.filtered(lambda inv: not inv.partner_id.email)
            invoices -= no_email_invoices

            info_txt = u"Relances email OK : %s\n" % len(invoices)
            info_txt += u"Relances email non OK : %s\n\n" % (len(no_remind_invoices) + len(no_email_invoices))

            if invoices:
                result['ok'] = True
                result['invoice_ids'] = [(6, 0, [invoices.ids])]
                if no_remind_invoices or no_email_invoices:
                    info_txt += u"Attention, seules les factures pour lesquelles la relance est OK seront traitées.\n\n"

            if no_remind_invoices or no_email_invoices:
                result['error'] = True
                info_txt += u"Détail des factures non OK :"
                if no_remind_invoices:
                    info_txt += u"\n- Les factures suivantes ne doivent pas être relancées :\n"
                    info_txt += u"\n".join(
                        ['    - %s' % (number or 'N/E') for number in no_remind_invoices.mapped('number')])
                if no_email_invoices:
                    info_txt += u"\n- Les clients des factures suivantes n'ont pas d'email :\n"
                    info_txt += u"\n".join(
                        ['    - %s' % (number or 'N/E') for number in no_email_invoices.mapped('number')])
            result['info_txt'] = info_txt
        return result

    invoice_ids = fields.Many2many(comodel_name='account.invoice', string=u"Factures à relancer")
    ok = fields.Boolean(default=False)
    error = fields.Boolean(default=False)
    info_txt = fields.Text()

    @api.multi
    def button_send_reminder(self):
        self.ensure_one()
        report_obj = self.env['report']
        for invoice in self.invoice_ids:
            mail_id = invoice.of_reminder_stage_id.email_template_id.send_mail(invoice.id)
            mail = self.env['mail.mail'].browse(mail_id)
            # On ajoute la facture PDF
            invoice_pdf = report_obj.get_pdf([invoice.id], 'account.report_invoice')
            mail.attachment_ids = [(0, 0, {'name': invoice.number + '.pdf',
                                           'datas_fname': invoice.number + '.pdf',
                                           'datas': base64.b64encode(invoice_pdf)})]
            mail.send()

            invoice.of_reminder_state = 'done'



