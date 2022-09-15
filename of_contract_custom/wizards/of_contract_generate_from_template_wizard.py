# -*- coding: utf-8 -*-

# 1: imports of python lib
# 2: imports of odoo
from odoo import models, fields, api
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class OFContractGenerateFromTemplateWizard(models.TransientModel):
    _name = 'of.contract.generate.from.template.wizard'

    contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat")
    contract_template_id = fields.Many2one(comodel_name='of.contract.template', string=u"Modèle de contrat")

    def button_confirm(self):
        vals = self.contract_template_id.template_to_record_vals()
        if vals.get('line_ids'):
            new_lines = vals.pop('line_ids')
            for _, _, line_vals in new_lines:
                line_vals['address_id'] = self.contract_id.partner_id.id
            vals['line_ids'] = new_lines
        self.contract_id.write(vals)
