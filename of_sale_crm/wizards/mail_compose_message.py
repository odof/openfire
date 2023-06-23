# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailComposeMessage(models.TransientModel):
    # todo: À adapter au nouveau système des custom documents OpenFire. mail.compose.message n'existe plus.
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if (
            self._context.get('default_model') == 'sale.order'
            and self._context.get('default_res_id')
            and self._context.get('of_mark_so_as_sent')
        ):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            order.of_sent_quotation = True
            self = self.with_context(mail_post_autofollow=True)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
