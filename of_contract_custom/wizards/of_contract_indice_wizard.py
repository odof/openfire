# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFContractIndiceWizard(models.TransientModel):
    _name = 'of.contract.indice.wizard'

    def _default_contracts(self):
        ids = self._context.get('active_ids')
        if not ids:
            return
        return self.env['of.contract'].browse(ids)

    indice_ids = fields.Many2many(comodel_name='of.index', string="Indices")
    contract_ids = fields.Many2many(
        comodel_name='of.contract', string="Contrats", default=lambda self: self._default_contracts())
    date_execution = fields.Date(string=u"Date de référence", default=fields.Date.today())

    @api.multi
    def button_apply(self):
        contracts = self.contract_ids.filtered('use_index')
        indices = self.indice_ids
        date_execution = self.date_execution
        products_done = 0
        for contract in contracts:
            contract_lines = contract.line_ids.filtered(lambda l: l.use_index and l.next_date and l.state == 'validated')
            for contract_line in contract_lines:
                product_lines = contract_line.contract_product_ids
                for product_line in product_lines:
                    previous_price = product_line.price_unit
                    # product = product_line.product_id
                    index_ids = product_line.product_id.categ_id.of_index_ids.ids
                    temp_indices = [indice for indice in indices if indice.id in index_ids]
                    additionnal_prices = []
                    for indice in temp_indices:
                        index_line = indice.index_line_ids.filtered(lambda il: il.date_start <= date_execution <= il.date_end)
                        if index_line:
                            additionnal_prices.append((previous_price * index_line.value) - previous_price)
                    if not additionnal_prices:
                        continue
                    new_price = previous_price + sum(additionnal_prices)
                    product_line.write({'price_unit': new_price, 'price_unit_prec': previous_price, 'date_indexed': fields.Date.today()})
                    products_done += 1
        return self.env['of.popup.wizard'].popup_return(message=u"%s articles ont été indéxés." % products_done, titre="Indexation")
