# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFContractCustomHook(models.AbstractModel):
    _name = 'of.contract.custom.hook'

    @api.model
    def _post_hook_v_10_0_2_1_0(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_contract_custom')])
        actions_todo = module_self and module_self.latest_version < '10.0.2.1.0'
        if actions_todo:
            contract_lines = self.env['of.contract.line'].with_context(no_verification=True).search(
                [('frequency_type', '=', 'date')])
            for contract_line in contract_lines:
                contract_line.old_next_date = contract_line.next_date
                done_services = contract_line.service_ids.filtered(
                    lambda s: not s.contract_invoice_id and s.state == 'done').sorted('date_last')
                invoices = contract_line.invoice_line_ids.mapped('invoice_id').sorted('date_invoice')
                if not done_services or not invoices:
                    continue
                for invoice in invoices:
                    if done_services:
                        done_services[0].contract_invoice_id = invoice.id
                        done_services -= done_services[0]
                contract_line._compute_dates()

    @api.model
    def _post_hook_v_10_0_2_1_1(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_contract_custom')])
        actions_todo = module_self and module_self.latest_version < '10.0.2.1.1'
        if actions_todo:
            contracts = self.env['of.contract'].search([])
            for contract in contracts:
                contract.write({'manager_id': contract.create_uid.id})
