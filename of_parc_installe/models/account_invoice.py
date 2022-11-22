# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_parc_installe_ids = fields.Many2many(comodel_name='of.parc.installe', string=u"Parcs installés")
    of_parc_count = fields.Integer(compute='_compute_parc_count')

    @api.multi
    def action_view_parc_installe(self):
        action = self.env.ref('of_parc_installe.action_view_of_parc_installe_sale').read()[0]
        action['domain'] = [('id', 'in', self.of_parc_installe_ids._ids)]
        return action

    @api.depends('of_parc_installe_ids')
    def _compute_parc_count(self):
        for invoice in self:
            invoice.of_parc_count = len(invoice.of_parc_installe_ids)
