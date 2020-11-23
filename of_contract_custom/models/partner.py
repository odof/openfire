# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_contrat_count = fields.Integer(compute="_compute_of_contrat_count")
    of_contrat_ids = fields.One2many('of.contract', 'partner_id', string="Contrats")

    @api.depends('of_contrat_ids')
    def _compute_of_contrat_count(self):
        for partner in self:
            partner.of_contrat_count = len(partner.of_contrat_ids)

    @api.multi
    def action_view_contrat(self):
        action = self.env.ref('of_contract_custom_v2.of_contract_custom_open_contrat').read()[0]
        action['domain'] = [('partner_id', 'in', self._ids)]
        return action

