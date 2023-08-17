# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def name_get(self):
        """Permet dans un Calcul de déperdition de chaleur de proposer les devis d'autres contacts entre parenthèses"""
        partner_id = self._context.get('partner_prio_id')
        if partner_id:
            result = []
            for rec in self:
                is_partner = rec.partner_id.id == partner_id
                result.append((rec.id, "%s%s%s" % ('' if is_partner else '(', rec.name, '' if is_partner else ')')))
            return result
        return super(SaleOrder, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un calcul de déperdition de chaleur de proposer en priorité les devis du contact"""
        if self._context.get('partner_prio_id'):
            partner_id = self._context['partner_prio_id']
            args = args or []
            res = super(SaleOrder, self).name_search(
                name,
                args + [['partner_id', '=', partner_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(SaleOrder, self).name_search(
                name,
                args + [['partner_id', '!=', partner_id]],
                operator,
                limit) or []
            return res
        return super(SaleOrder, self).name_search(name, args, operator, limit)
