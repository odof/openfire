# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import RedirectWarning

from odoo.addons.account.models.account_move import AccountMove

NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')


# We are 🐒-patching the following methods :
#    - account.move._onchange_partner_id()
# We are adding the following methods :
#    - _onchange_partner_id_warning()
class OfAccountMoveHooks(models.AbstractModel):
    """When you use monkey patching, the code is executed when the module
    is in the addons_path of the Odoo server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    """

    _name = 'of.account.move.hooks.installed'
    _description = "This model is used to test if the module is installed and avoid monkey patching side-effects."


_onchange_partner_id_original = AccountMove._onchange_partner_id


@api.onchange('partner_id')
def _onchange_partner_id(self):
    """Patched method to remove the warning part of the original method."""
    if self.env.get('of.account.move.hooks.installed') is None:
        return _onchange_partner_id_original(self)

    self = self.with_company(self.journal_id.company_id)

    if self.partner_id:
        rec_account = self.partner_id.property_account_receivable_id
        pay_account = self.partner_id.property_account_payable_id
        if not rec_account and not pay_account:
            action = self.env.ref('account.action_account_config')
            msg = _(
                "Cannot find a chart of accounts for this company, You should configure it. "
                "\nPlease go to Account Configuration."
            )
            raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))


@api.onchange('partner_id')
def _onchange_partner_id_warning(self):
    """Patched method to split the warning part in a separate method, that we can override."""
    self = self.with_company(self.journal_id.company_id)

    warning = {}
    if p := self.partner_id:
        if p.invoice_warn == 'no-message' and p.parent_id:
            p = p.parent_id
        if p.invoice_warn and p.invoice_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                p = p.parent_id
            warning = {'title': _("Warning for %s") % p.name, 'message': p.invoice_warn_msg}
            if p.invoice_warn == 'block':
                self.partner_id = False
            return {'warning': warning}


AccountMove._onchange_partner_id = _onchange_partner_id
AccountMove._onchange_partner_id_warning = _onchange_partner_id_warning
