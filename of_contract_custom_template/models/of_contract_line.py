# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFContractLine(models.Model):
    _inherit = 'of.contract.line'

    @api.multi
    def copy_contract_line(self):
        self.ensure_one()
        self.copy_line()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
