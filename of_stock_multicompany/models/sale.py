# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.tools import pickle


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        pass

    @api.model
    def get_default_warehouse_id_for_company(self, company_id):
        # 1. look up context
        if 'default_warehouse_id' in self._context:
            return self._context['default_warehouse_id']

        # 2. look up ir_values
        self._cr.execute(
            "SELECT value "
            "FROM ir_values "
            "WHERE key = 'default' AND model = 'sale.order' AND name = 'warehouse_id' "
            "  AND (user_id = %s OR user_id IS NULL) "
            "  AND (company_id IS NULL or company_id = %s) "
            "ORDER BY user_id, company_id "
            "LIMIT 1",
            (self._uid, company_id)
        )
        res = self._cr.fetchone()
        if res:
            value = pickle.loads(res[0].encode('utf-8'))
            return value

        # 3. look up field.default
        return self.env['res.company'].browse(company_id).of_default_warehouse_id.id

    @api.model
    def create(self, vals):
        if 'company_id' in vals and 'warehouse_id' not in vals:
            # Si on laisse le calcul de valeurs par défaut, c'est la société de l'utilisateur qui sera utilisée
            #   lors de la recherche dans ir.values.
            # On doit donc reproduire le calcul de valeurs par défaut de _default_get() mais avec la société
            #   fournie dans vals.
            vals['warehouse_id'] = self.get_default_warehouse_id_for_company(vals['company_id'])
        return super(SaleOrder, self).create(vals)
