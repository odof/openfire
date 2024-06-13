# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_id.update_account()
        return super()._onchange_partner_id()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if partner_id := vals['partner_id']:
                partner = self.env['res.partner'].browse(partner_id)
                partner.update_account()
        return super().create(vals_list)
