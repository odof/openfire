# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_contract_ids = fields.One2many(comodel_name='of.contract', inverse_name='order_id', string=u"Contrats")
    of_contract_count = fields.Integer(string=u"Nb de contrats", compute='_compute_of_contract_count')

    @api.depends('of_contract_ids')
    def _compute_of_contract_count(self):
        for record in self:
            record.of_contract_count = len(record.of_contract_ids)

    @api.multi
    def action_view_contract(self):
        if self.ensure_one():
            contracts = self.of_contract_ids
            return {
                'name': u"Contrats",
                'view_mode': 'tree,kanban,form',
                'view_type': 'form',
                'res_model': 'of.contract',
                'domain': "[('id', 'in', %s)]" % contracts.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def _create_contract_from_template(self):
        contract_obj = self.env['of.contract']
        for rec in self:
            if rec.of_template_id.of_contract_tmpl_id:
                contract = rec.of_template_id.of_contract_tmpl_id
                vals = rec._get_contract_vals()
                contract_id = contract_obj.create(vals)
                lines = [(5, 0, 0)]
                for line in contract.line_ids:
                    line_vals = rec.get_contract_line_vals(line)
                    lines.append((0, 0, line_vals))
                contract_id.line_ids = lines
                rec.of_contract_ids = rec.of_contract_ids + contract_id

    @api.multi
    def action_verification_confirm(self):
        res = super(SaleOrder, self).action_verification_confirm()
        self._create_contract_from_template()
        return res

    @api.multi
    def _get_contract_vals(self):
        self.ensure_one()
        contract = self.of_template_id.of_contract_tmpl_id
        if not contract:
            return {}
        contract_vals = contract.get_contract_vals()
        contract_vals.update(
            {
                'reference': self.name,
                'partner_id': self.partner_invoice_id.id,
                'company_id': self.company_id.id,
                'date_souscription': fields.Date.to_string(fields.Date.from_string(self.confirmation_date)),
                'manager_id': self.user_id.id,
                'order_id': self.id,
                'sale_type_id': self.of_sale_type_id.id,
                'date_start': fields.Date.to_string(fields.Date.from_string(self.confirmation_date)),
            }
        )
        return contract_vals

    @api.multi
    def get_contract_line_vals(self, contract_tmpl_line):
        self.ensure_one()
        line_vals = contract_tmpl_line.get_contract_line_vals()
        address = self.partner_shipping_id
        parcs = self.of_parc_installe_ids.filtered(lambda r: r.site_adresse_id == address)
        line_vals.update(
            {
                'address_id': address.id,
                'fiscal_position_id': self.of_template_id.of_contract_tmpl_id.property_fiscal_position_id.id,
                'parc_installe_id': parcs and parcs[0].id or False,
            }
        )
        return line_vals
