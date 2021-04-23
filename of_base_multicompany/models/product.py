# -*- coding: utf-8 -*-
from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _set_standard_price(self, value):
        # Pour rester en accord avec le fonctionnement de standard_price, l'historique du coût est conservé
        # au niveau de la société comptable
        company_id = self._context.get('force_company', self.env.user.company_id.id)
        company = self.env['res.company'].browse(company_id).accounting_company_id
        if company.id != company_id:
            self = self.with_context(force_company=company.id)
        super(ProductProduct, self)._set_standard_price(value)

    @api.multi
    def get_history_price(self, company_id, date=None):
        company = self.env['res.company'].browse(company_id)
        return super(ProductProduct, self).get_history_price(company.accounting_company_id.id, date=date)
