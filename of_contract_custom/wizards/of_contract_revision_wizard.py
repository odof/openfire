# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFContractAvenantWizard(models.TransientModel):
    _name = 'of.contract.revision.wizard'

    contract_id = fields.Many2one('of.contract', string="Contrat")
    period_id = fields.Many2one(
        comodel_name='of.contract.period', string=u"Période à réviser",
        domain="[('contract_id', '=', contract_id), ('has_invoices', '=', True)]", required=True)
    message = fields.Text(string="Message")

    @api.multi
    def button_create(self):
        invoices = self.contract_id.generate_revision_invoice(self.period_id.date_end)
        if not invoices:
            self.message = "Aucune facture de révision à créer."
            return {'type': 'ir.actions.do_nothing'}
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
