# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def reflect_code_prefix_change(self, old_code, new_code, digits):
        return super(ResCompany, self.with_context(reflect_code_change=True)).reflect_code_prefix_change(
            old_code, new_code, digits
        )

    def reflect_code_digits_change(self, digits):
        return super(ResCompany, self.with_context(reflect_code_change=True)).reflect_code_digits_change(digits)
