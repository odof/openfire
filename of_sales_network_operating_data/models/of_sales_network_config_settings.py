# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSalesNetworkConfigSettings(models.TransientModel):
    _inherit = 'of.sales.network.config.settings'

    esb_url = fields.Char(string=u"URL d'accès à l'ESB")
    esb_login = fields.Char(string=u"Identifiant de connexion à l'ESB")
    esb_password = fields.Char(string=u"Mot de passe de connexion à l'ESB")

    @api.multi
    def set_esb_url_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.sales.network.config.settings', 'esb_url', self.esb_url)

    @api.multi
    def set_esb_login_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.sales.network.config.settings', 'esb_login', self.esb_login)

    @api.multi
    def set_esb_password_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.sales.network.config.settings', 'esb_password', self.esb_password)
