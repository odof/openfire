# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFContract(models.Model):
    _inherit = 'of.contract'

    contract_tmpl_id = fields.Many2one(comodel_name='of.contract.template', string=u"Modèle de contrat")
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Devis", readonly=True)

    @api.onchange('contract_tmpl_id')
    def _onchange_contract_tmpl_id(self):
        for rec in self:
            if rec.contract_tmpl_id:
                rec.update(rec.contract_tmpl_id.get_contract_vals())

    @api.multi
    def update_lines(self):
        contract_line_obj = self.env['of.contract.line']
        for rec in self:
            for line in rec.contract_tmpl_id.line_ids:
                line_vals = line.get_contract_line_vals()
                line_vals.update({
                    'contract_id': rec.id,
                    'fiscal_position_id': rec.fiscal_position_id.id,
                    'address_id': rec.partner_id.id,
                })
                contract_line_obj.create(line_vals)
