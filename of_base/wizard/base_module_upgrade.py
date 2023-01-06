# -*- coding: utf-8 -*-

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from passlib.context import CryptContext


class BaseModuleUpgrade(models.TransientModel):
    _inherit = "base.module.upgrade"

    of_validation_code = fields.Char(string="Code de validation")

    @api.multi
    def upgrade_module(self):
        if self.env['ir.module.module'].search([('state', '=', 'to remove')], limit=1):
            hashed_password = odoo.tools.config.get('of_module_uninstall_password')
            validation_code = len(self) == 1 and self.of_validation_code or ""

            # On utilise le même outil de cryptage que pour les mots de passe des utilisateurs
            if not CryptContext(['pbkdf2_sha512']).verify(validation_code, hashed_password):
                raise UserError(_("Le code de validation est incorrect."))
        return super(BaseModuleUpgrade, self).upgrade_module()
