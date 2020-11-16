# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class OFContractLineCancelWizard(models.TransientModel):
    _name = 'of.contract.line.cancel.wizard'

    contract_line_id = fields.Many2one('of.contract.line', string="Ligne d'origine")
    date_end = fields.Date(string="Date de fin")

    @api.multi
    def button_end(self):
        self.contract_line_id.write({
            'date_end'       : self.date_end,
            })
