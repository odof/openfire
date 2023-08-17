# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    @api.multi
    def name_get(self):
        """Permet dans un Calcul de déperdition de chaleur de proposer les appareils d'autres contacts
            entre parenthèses
        """
        partner_id = self._context.get('partner_prio_id')
        if partner_id:
            result = []
            for rec in self:
                is_partner = rec.client_id.id == partner_id
                result.append((rec.id, "%s%s%s" % ('' if is_partner else '(', rec.name, '' if is_partner else ')')))
            return result
        return super(OFParcInstalle, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un calcul de déperdition de chaleur de proposer en priorité les appareils du contact"""
        if self._context.get('partner_prio_id'):
            partner_id = self._context['partner_prio_id']
            args = args or []
            res = super(OFParcInstalle, self).name_search(
                name,
                args + [['client_id', '=', partner_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(OFParcInstalle, self).name_search(
                name,
                args + [['client_id', '!=', partner_id]],
                operator,
                limit) or []
            return res
        return super(OFParcInstalle, self).name_search(name, args, operator, limit)
