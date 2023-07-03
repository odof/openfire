# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    of_mandatory_siren = fields.Boolean(
        string=u"(OF) SIREN/NIC obligatoire", default=lambda s:s._get_of_mandatory_siren_default())

    @api.model
    def _get_of_mandatory_siren_default(self):
        view = self.env.ref('of_l10n_fr_siret.res_partner_view_form')
        if not view or not view.active:
            return False
        return True

    @api.multi
    def set_of_mandatory_siren_default(self):
        view = self.env.ref('of_l10n_fr_siret.res_partner_view_form')
        if view:
            view.write({'active': self.of_mandatory_siren})
