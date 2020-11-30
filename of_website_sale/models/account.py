# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.of_account_tax.models.of_account_tax import AccountFiscalPosition


@api.multi
def map_tax(self, taxes, product=None, partner=None):
    if not self._context.get('website_id', False):
        if not self:
            raise UserError(u"Veuillez renseigner une position fiscale")
        self.ensure_one()
    if len(self) == 1 and not taxes:
        taxes = self.default_tax_ids
    return super(AccountFiscalPosition, self).map_tax(taxes, product=product, partner=partner)


AccountFiscalPosition.map_tax = map_tax
