# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFPlanningContractWizard(models.TransientModel):
    _name = 'of.contract.planning.wizard'

    def button_invoice(self):
        ids = self._context.get('active_ids', False)
        if ids:
            invoices = self.env['of.contract'].browse(ids).recurring_create_invoice()
            action = self.env.ref('account.action_invoice_tree1').read()[0]
            if len(invoices) > 1:
                action['domain'] = [('id', 'in', list(invoices._ids))]
            elif len(invoices) == 1:
                action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action
