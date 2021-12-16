# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class OFContractAvenantWizard(models.TransientModel):
    _name = 'of.contract.avenant.wizard'

    contract_line_id = fields.Many2one('of.contract.line', string="Ligne d'origine")
    date_start = fields.Date(string="Date de prise d'effet")

    @api.multi
    def button_create(self):
        contract_line_obj = self.env['of.contract.line']
        origine = self.contract_line_id
        data = origine.copy_data(default={
            'state': 'draft',
            'date_avenant': self.date_start,
            'type': 'avenant',
            'revision_avenant': self.contract_line_id.recurring_invoicing_payment_id.code == 'pre-paid',
        })[0]
        line_data = []
        for line in origine.contract_product_ids:
            line_data.append((0, 0, line.copy_data(default={'previous_product_id': line.id})[0]))
        data['contract_product_ids'] = line_data
        avenant = contract_line_obj.create(data)
        origine.with_context(no_verification=True).write({
            'line_avenant_id': avenant.id,
            'date_end'       : fields.Date.to_string(fields.Date.from_string(self.date_start) - relativedelta(days=1)),
            })
        origine.remove_services()
        view_id = self.env.ref('of_contract_custom.of_contract_line_view_form_extended').id
        return {
            'name'     : 'Ligne de contrat (avenant)',
            'type'     : 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.contract.line',
            'views'    : [(view_id, 'form')],
            'view_id'  : view_id,
            'target'   : 'new',
            'res_id'   : avenant.id,
            'context'  : self.env.context}
