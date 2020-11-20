# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.of_utils.models.of_utils import format_date


class OFContractLineCancelWizard(models.TransientModel):
    _name = 'of.contract.line.cancel.wizard'

    contract_line_id = fields.Many2one('of.contract.line', string="Ligne d'origine")
    date_end = fields.Date(string="Date de fin")

    @api.onchange('date_end')
    def onchange_date_end(self):
        if self.contract_line_id.contract_id.date_end and self.date_end > self.contract_line_id.contract_id.date_end:
            lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
            raise UserError(u"Vous ne pouvez sélectionner une date de fien supérieure à la date de fin du contrat. "
                            u"(%s)" % format_date(self.contract_line_id.contract_id.date_end, lang))


    @api.multi
    def button_end(self):
        if self.contract_line_id.contract_id.date_end and self.date_end > self.contract_line_id.contract_id.date_end:
            lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
            raise UserError(u"Vous ne pouvez sélectionner une date de fien supérieure à la date de fin du contrat. "
                            u"(%s)" % format_date(self.contract_line_id.contract_id.date_end, lang))
        self.contract_line_id.write({
            'date_end'       : self.date_end,
            })
