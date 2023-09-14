# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    of_heat_loss_ids = fields.One2many(
        comodel_name='of.calculation.heat.loss', inverse_name='lead_id', string=u"Calcul déperdition de chaleur")
    of_heat_loss_count = fields.Integer(
        string=u"Calcul déperdition de chaleur (compteur)", compute='_compute_of_heat_loss_count')

    @api.depends('of_heat_loss_ids')
    def _compute_of_heat_loss_count(self):
        for lead in self:
            lead.of_heat_loss_count = len(lead.of_heat_loss_ids)

    @api.multi
    def name_get(self):
        """Permet dans un Calcul de déperdition de chaleur de proposer les opportunités d'autres contacts
            entre parenthèses
        """
        partner_id = self._context.get('partner_prio_id')
        if partner_id:
            result = []
            for rec in self:
                is_partner = rec.partner_id.id == partner_id
                result.append((rec.id, "%s%s%s" % ('' if is_partner else '(', rec.name, '' if is_partner else ')')))
            return result
        return super(CRMLead, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un calcul de déperdition de chaleur de proposer en priorité les opportunités du contact"""
        if self._context.get('partner_prio_id'):
            partner_id = self._context['partner_prio_id']
            args = args or []
            res = super(CRMLead, self).name_search(
                name,
                args + [['partner_id', '=', partner_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(CRMLead, self).name_search(
                name,
                args + [['partner_id', '!=', partner_id]],
                operator,
                limit) or []
            return res
        return super(CRMLead, self).name_search(name, args, operator, limit)

    @api.multi
    def action_view_calculation_heat_loss(self):
        heat_loss_calculations = self.of_heat_loss_ids
        action = self.env.ref('of_calculation_heat_loss.of_calculation_heat_loss_action').read()[0]
        if len(heat_loss_calculations) > 1:
            action['domain'] = [('id', 'in', heat_loss_calculations.ids)]
        elif len(heat_loss_calculations) == 1:
            action['views'] = [(self.env.ref('of_calculation_heat_loss.of_calculation_heat_loss_form_view').id, 'form')]
            action['res_id'] = heat_loss_calculations.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
