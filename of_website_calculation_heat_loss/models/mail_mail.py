# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.multi
    def _postprocess_sent_message(self, mail_sent=True):
        if self._context.get('heat_loss_mail_attempt'):
            mails = self.filtered(lambda m: m.model == 'of.calculation.heat.loss')
            heat_loss = self.env['of.calculation.heat.loss'].browse(mails.mapped('res_id')).exists()
            if heat_loss:
                heat_loss.write({'mailing_attempt': mail_sent and 'success' or 'failed'})
        return super(MailMail, self)._postprocess_sent_message(mail_sent=mail_sent)
