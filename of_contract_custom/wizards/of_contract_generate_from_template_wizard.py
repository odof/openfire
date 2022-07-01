# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFContractGenerateFromTemplateWizard(models.TransientModel):
    _name = 'of.contract.generate.from.template.wizard'

    contract_id = fields.Many2one(comodel_name='of.contract')
    contract_template_id = fields.Many2one(comodel_name='of.contract.template', string=u"Modèle de contrat")

    def button_confirm(self):
        vals = self.contract_template_id.template_to_record_vals()
        if vals.get('line_ids'):
            new_lines = vals.pop('line_ids')
            for _, _, line_vals in new_lines:
                line_vals['address_id'] = self.contract_id.partner_id.id
            vals['line_ids'] = new_lines
        self.contract_id.write(vals)
