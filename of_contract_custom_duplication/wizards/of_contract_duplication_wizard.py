# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OFContractDuplicationWizard(models.TransientModel):
    _name = 'of.contract.duplication.wizard'

    def _get_default_contract_period(self):
        active_contract = self._context.get('active_id')
        if active_contract:
            contract = self.env['of.contract'].browse(active_contract)
            return contract.date_start, contract.date_end

    def _get_count_duplicated_cancelled_lines(self):
        active_contract = self._context.get('active_id')
        if active_contract:
            contract = self.env['of.contract'].browse(active_contract)
            contract_date_end = contract.date_end
            line_count = len(contract.line_ids)
            cancelled_line_count = 0
            for line in contract.line_ids:
                if line.state == 'cancel' or (
                    (contract_date_end and line.date_end) and line.date_end < contract_date_end
                ):
                    cancelled_line_count += 1
            duplicated_line_count = line_count - cancelled_line_count
            return duplicated_line_count, cancelled_line_count

    def _get_renewal_contract(self):
        active_contract = self._context.get('active_id')
        if active_contract:
            contract = self.env['of.contract'].browse(active_contract)
            return contract.renewal

    date_start = fields.Date(string=u"Début", default=lambda r: r._get_default_contract_period()[0], required=True)
    date_end = fields.Date(string=u"Fin", default=lambda r: r._get_default_contract_period()[1])
    duplicated_lines = fields.Integer(
        string=u"Lignes dupliquées", default=lambda r: r._get_count_duplicated_cancelled_lines()[0], readonly=True
    )
    cancelled_lines = fields.Integer(
        string=u"Lignes annulées", default=lambda r: r._get_count_duplicated_cancelled_lines()[1], readonly=True
    )
    renewal = fields.Boolean(string="Renouvellement automatique", default=lambda r: r._get_renewal_contract())

    @api.constrains('date_start', 'date_end')
    def date_constrains(self):
        if (self.date_start and self.date_end) and (self.date_start > self.date_end):
            raise ValidationError(u"La date de fin doit être supérieure à la date de début du contrat !")

    @api.onchange('renewal')
    def _onchange_renewal(self):
        if self.renewal:
            self.date_end = False
        else:
            date = fields.Date.from_string(self.date_start)
            end_date = date + relativedelta(years=1, day=1, month=1) - relativedelta(days=1)
            self.date_end = fields.Date.to_string(end_date)

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.renewal:
            self.date_end = False
        else:
            date = fields.Date.from_string(self.date_start)
            end_date = date + relativedelta(years=1, days=-1)
            self.date_end = fields.Date.to_string(end_date)

    @api.multi
    def button_duplicate_contract(self):
        active_contract = self._context.get('active_id')
        if active_contract:
            contract = self.env['of.contract'].browse(active_contract)
            contract_date_end = contract.date_end
            contract_obj = self.env['of.contract']
            contract_line_obj = self.env['of.contract.line']
            new_contract_vals = contract.copy_contract_vals(self.date_start, self.date_end, self.renewal)
            new_contract = contract_obj.create(new_contract_vals)
            for line in contract.line_ids:
                if not (
                    line.state == 'cancel'
                    or ((contract_date_end and line.date_end) and line.date_end < contract_date_end)
                ):
                    new_line_vals = line.copy_contract_line_vals(new_contract)
                    contract_line_obj.create(new_line_vals)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Contrat',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.contract',
                'res_id': new_contract.id,
                'target': 'current',
                'flags': {'initial_mode': 'edit', 'form': {'options': {'mode': 'edit'}}},
            }
