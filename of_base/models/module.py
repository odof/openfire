# -*- coding: utf-8 -*-

import re
from odoo import models, api, _
from odoo.exceptions import UserError


class Module(models.Model):
    _inherit = 'ir.module.module'

    @api.multi
    def write(self, vals):
        if vals.get('state', '') == 'to remove':
            forbidden_uninstall = {
                'of_base,',
                'of_obligatoire',
                'of_sale',
            }
            illegal_uninstall = forbidden_uninstall & set(self.mapped('name'))
            if illegal_uninstall:
                raise UserError(
                    _(u"Vous tentez de supprimer un ou plusieurs modules protégés : %s" + ", ".join(illegal_uninstall)))
        return super(Module, self).write(vals)
