# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.sale.wizard.mail_compose_message import MailComposeMessage

# We are 🐒-patching the following methods :
#    - sale.wizard.mail_compose_message._action_send_mail()

_action_send_mail_original = MailComposeMessage._action_send_mail


class OFSaleHooks(models.AbstractModel):
    """When you use monkey patching, the code is executed when the module
    is in the addons_path of the Odoo server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    """

    _name = 'of.sale.hooks.installed'
    _description = "This model is used to test if the module is installed and avoid monkey patching side-effects."


def _action_send_mail(self, auto_commit=False):
    if self.env.get('of.sale.hooks.installed') is None:
        return _action_send_mail_original(self, auto_commit=auto_commit)
    if self.model == 'sale.order':
        self = self.with_context(mailing_document_based=True)
        if self.env.context.get('of_mark_so_as_sent') and self.template_id and not self.template_id.of_copy_to_sender:
            self = self.with_context(mail_notify_author=self.env.user.partner_id in self.partner_ids)
    return super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)


MailComposeMessage._action_send_mail = _action_send_mail
