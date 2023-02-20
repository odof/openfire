# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def get_supported_account_types(self):
        return self._get_supported_account_types()

    @api.model
    def _get_supported_account_types(self):
        return [('bank', _('Bank')), ('iban', _('IBAN'))]

    acc_type = fields.Selection(
        selection=lambda x: x.env['res.partner.bank'].get_supported_account_types(),
        compute='_compute_acc_type', inverse='_inverse_acc_type', store=True,
        string="Type of account", required=True, default='iban',
        help="Leave the account type IBAN to let the software check the validity of the entered code."
             "Use the Bank type for any other type of account, no verification will be performed.")

    def _inverse_acc_type(self):
        pass

    def write(self, vals):
        if vals.get('acc_type') != 'iban' or 'acc_number' in vals:
            return super().write(vals)
        for bank in self:
            # On ajoute acc_number dans vals pour forcer son nettoyage dans le module base_iban
            vals['acc_number'] = bank.acc_number
            res = super(ResPartnerBank, bank).write(vals)
        return res
