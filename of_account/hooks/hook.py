# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFAccountHook(models.AbstractModel):
    _name = 'of.account.hook'

    @api.model
    def _update_version_10_0_2_1_0_hook(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_account'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self and module_self.latest_version and module_self.latest_version < '10.0.2.1.0':
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            to_install = self.env["ir.module.module"].search(
                [
                    ("name", "=", "l10n_fr_einvoicing_openfire"),
                    ("state", "=", "uninstalled"),
                ]
            )
            fr_companies = self.env["res.company"].search([("partner_id.country_id.code", "=", "FR")])
            if to_install and fr_companies:
                to_install.sudo().button_install()
