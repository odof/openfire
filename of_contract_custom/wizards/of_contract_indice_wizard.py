# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFContractIndiceWizard(models.TransientModel):
    _name = 'of.contract.indice.wizard'

    def _default_contracts(self):
        ids = self._context.get('active_ids')
        if not ids:
            return
        return self.env['of.contract'].browse(ids)

    rollback = fields.Boolean(string=u"Retour au PU précédent")
    indice_ids = fields.Many2many(comodel_name='of.index', string="Indices")
    contract_ids = fields.Many2many(
        comodel_name='of.contract', string="Contrats", default=lambda self: self._default_contracts())
    date_execution = fields.Date(string=u"Date de référence", default=fields.Date.today())

    line_ids = fields.One2many(comodel_name='of.contract.indice.line.wizard', inverse_name='wizard_id', string="Lignes affectées", compute="_compute_line_ids")

    @api.onchange('contract_ids', 'rollback', 'indice_ids', 'date_execution')
    def _compute_line_ids(self):
        wizard_lines_obj = self.env['of.contract.indice.line.wizard']
        for wizard in self:
            new_lines = wizard_lines_obj
            contracts = wizard.contract_ids.filtered('use_index')
            indices = wizard.indice_ids
            date_execution = wizard.date_execution
            for contract in contracts:
                contract_lines = contract.line_ids.filtered(
                    lambda l: l.use_index and l.next_date and l.state == 'validated')
                for contract_line in contract_lines:
                    product_lines = contract_line.contract_product_ids
                    for product_line in product_lines:
                        if wizard.rollback:
                            previous_price = product_line.price_unit
                            new_price = product_line.price_unit_prec
                            new_lines += wizard_lines_obj.new({
                                'product_line_id': product_line.id,
                                'current_price'  : previous_price,
                                'new_price'      : new_price,
                            })
                        else:
                            previous_price = product_line.price_unit
                            # product = product_line.product_id
                            index_ids = product_line.product_id.categ_id.of_index_ids.ids
                            temp_indices = [indice for indice in indices if indice.id in index_ids]
                            additionnal_prices = []
                            for indice in temp_indices:
                                index_line = indice.index_line_ids.filtered(
                                    lambda il: il.date_start <= date_execution <= il.date_end)
                                if index_line:
                                    additionnal_prices.append((previous_price * index_line.value) - previous_price)
                            if not additionnal_prices:
                                new_lines += wizard_lines_obj.new({
                                    'product_line_id': product_line.id,
                                    'current_price'  : previous_price,
                                    'new_price'      : previous_price,
                                    })
                            else:
                                new_price = previous_price + sum(additionnal_prices)
                                new_lines += wizard_lines_obj.new({
                                    'product_line_id': product_line.id,
                                    'current_price'  : previous_price,
                                    'new_price'      : new_price,
                                    })
            wizard.line_ids = new_lines

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
                    if self.rollback:
                        previous_price = product_line.price_unit
                        new_price = product_line.price_unit_prec
                        product_line.with_context(no_verification=True).write({'price_unit': new_price, 'price_unit_prec': previous_price, 'date_indexed': fields.Date.today()})
                        products_done += 1
                    else:
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
                        product_line.with_context(no_verification=True).write({'price_unit': new_price, 'price_unit_prec': previous_price, 'date_indexed': fields.Date.today()})
                        products_done += 1
        message = u"%s articles %s été %s." % (products_done, products_done == 1 and u'à' or u'ont',
                                               self.rollback and u"retournés au prix précédent" or u"indéxés")
        return self.env['of.popup.wizard'].popup_return(message=message, titre="Indexation")


class OFContractIndiceLineWizard(models.TransientModel):
    _name = 'of.contract.indice.line.wizard'

    wizard_id = fields.Many2one(comodel_name='of.contract.indice.wizard', string="Wizard")
    product_line_id = fields.Many2one(comodel_name='of.contract.product', string="Produit du contrat")
    contract_line_id = fields.Many2one(comodel_name='of.contract.line', string="Ligne de contrat", related="product_line_id.line_id")
    product_id = fields.Many2one(comodel_name='product.product', string="Article", related="product_line_id.product_id")
    current_price = fields.Float(string="PU Actuel")
    new_price = fields.Float(string=u"PU calculé")
