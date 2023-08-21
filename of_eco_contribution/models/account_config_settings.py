# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    @api.model
    def _auto_init(self):
        super(AccountConfigSettings, self)._auto_init()
        if self.env['ir.values'].get_default('account.config.settings', 'of_eco_contribution_price_included') is None:
            self.env['ir.values'].set_default('account.config.settings', 'of_eco_contribution_price_included', True)

    of_eco_contribution_price_included = fields.Boolean(
        string=u"(OF) Inclure dans le prix", default=True,
        help=u"Si coché, l'éco-contribution est incluse dans le prix de l'article. "
             u"Sinon, elle sera rajoutée au prix unitaire de la ligne de commande")

    @api.multi
    def set_of_eco_contribution_price_included(self):
        return self.env['ir.values'].sudo().set_default(
            'account.config.settings', 'of_eco_contribution_price_included', self.of_eco_contribution_price_included)
