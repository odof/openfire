# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.of_utils.models.of_utils import format_date


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
    date_execution = fields.Date(
        string=u"Date de la période d'indexation", default=fields.Date.today(),
        help=u"Cette date vous permet de sélectionner la valeur de l'indexation que vous souhaitez appliquer, "
             u"elle doit être comprise dans la période définie de l'une des valeurs d'indexation définies "
             u"dans votre indice")
    purchase = fields.Boolean(string=u"Affecte le coÛt", default=True)

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
                        lambda l: l.use_index and
                                  (not l.date_contract_end or l.date_contract_end > fields.Date.today())
                                  and l.state == 'validated')
                for contract_line in contract_lines:
                    product_lines = contract_line.contract_product_ids
                    for product_line in product_lines:
                        if wizard.rollback:
                            current_price = product_line.price_unit
                            previous_price = product_line.price_unit_prec
                            current_purchase_price = product_line.purchase_price
                            new_values = {
                                'product_line_id'       : product_line.id,
                                'current_price'         : current_price,
                                'new_price'             : previous_price,
                                'current_purchase_price': current_purchase_price,
                                'new_purchase_price'    : current_purchase_price,
                            }
                            if self.purchase:
                                previous_purchase_price = product_line.purchase_price_prec
                                new_values.update({
                                    'new_purchase_price': previous_purchase_price,
                                })
                            new_lines += wizard_lines_obj.new(new_values)
                        else:
                            previous_price = product_line.price_unit
                            previous_purchase_price = product_line.purchase_price
                            # product = product_line.product_id
                            index_ids = product_line.product_id.of_index_ids.ids
                            temp_indices = [indice for indice in indices if indice.id in index_ids]
                            additionnal_prices = []
                            additionnal_purchase_prices = []
                            for indice in temp_indices:
                                index_line = indice.index_line_ids.filtered(
                                    lambda il: il.date_start <= date_execution <= il.date_end)
                                if index_line:
                                    additionnal_prices.append((previous_price * index_line.value) - previous_price)
                                    additionnal_purchase_prices.append(
                                            (previous_purchase_price * index_line.value) - previous_purchase_price)
                            if not additionnal_prices:
                                new_lines += wizard_lines_obj.new({
                                    'product_line_id'       : product_line.id,
                                    'current_price'         : previous_price,
                                    'new_price'             : previous_price,
                                    'current_purchase_price': previous_purchase_price,
                                    'new_purchase_price'    : previous_purchase_price,
                                })
                            else:
                                new_price = previous_price + sum(additionnal_prices)
                                new_values = {
                                    'product_line_id'       : product_line.id,
                                    'current_price'         : previous_price,
                                    'new_price'             : new_price,
                                    'current_purchase_price': previous_purchase_price,
                                    'new_purchase_price'    : previous_purchase_price,
                                }
                                if self.purchase:
                                    new_purchase_price = previous_purchase_price + sum(additionnal_purchase_prices)
                                    new_values.update({
                                        'new_purchase_price'    : new_purchase_price,
                                })
                                new_lines += wizard_lines_obj.new(new_values)
            wizard.line_ids = new_lines

    @api.multi
    def button_apply(self):
        contracts = self.contract_ids.filtered('use_index')
        indices = self.indice_ids
        date_execution = self.date_execution
        products_done = self.env['of.contract.product']

        for contract in contracts:
            contract_lines = contract.line_ids.filtered(
                    lambda l: l.use_index and
                              (not l.date_contract_end or l.date_contract_end > fields.Date.today())
                              and l.state == 'validated')
            for contract_line in contract_lines:
                product_lines = contract_line.contract_product_ids
                for product_line in product_lines:
                    if self.rollback:
                        new_price = product_line.price_unit_prec
                        new_values = {
                            'price_unit'        : new_price,
                            'date_indexed'      : product_line.date_indexed_prec,
                            'date_indexed_prec' : False,
                        }
                        if self.purchase:
                            new_purchase_price = product_line.purchase_price_prec
                            new_values.update({
                                'purchase_price'    : new_purchase_price,
                            })
                        product_line.with_context(no_verification=True).write(new_values)
                        products_done |= product_line
                    else:
                        previous_price = product_line.price_unit
                        previous_purchase_price = product_line.purchase_price
                        # product = product_line.product_id
                        index_ids = product_line.product_id.of_index_ids.ids
                        temp_indices = [indice for indice in indices if indice.id in index_ids]
                        additionnal_prices = []
                        additionnal_purchase_prices = []
                        for indice in temp_indices:
                            index_line = indice.index_line_ids.filtered(lambda il: il.date_start <= date_execution <= il.date_end)
                            if index_line:
                                additionnal_prices.append((previous_price * index_line.value) - previous_price)
                                additionnal_purchase_prices.append(
                                    (previous_purchase_price * index_line.value) - previous_purchase_price)
                        if not additionnal_prices:
                            continue
                        new_price = previous_price + sum(additionnal_prices)
                        new_values = {
                            'product_line_id'    : product_line.id,
                            'price_unit_prec'    : previous_price,
                            'price_unit'         : new_price,
                            'purchase_price'     : previous_purchase_price,
                            'purchase_price_prec': previous_purchase_price,
                        }
                        if self.purchase:
                            new_purchase_price = previous_purchase_price + sum(additionnal_purchase_prices)
                            new_values.update({
                                'purchase_price': new_purchase_price,
                            })
                        product_line.with_context(no_verification=True).write(new_values)
                        products_done |= product_line
        products_done_count = len(products_done)
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for contract in products_done.mapped('line_id').mapped('contract_id'):
            products = products_done.filtered(lambda p: p.line_id.contract_id.id == contract.id)
            today = format_date(fields.Date.today(), lang)
            if self.rollback:
                contract.message_post(u"Retour au PU précédent réalisée le %s pour les articles :<br/>%s" %
                                      (today, '<br/>'.join([product.product_id.name for product in products])))
            else:
                contract.message_post(u"Indexation réalisée le %s pour les articles :<br/>%s" %
                                      (today, '<br/>'.join([product.product_id.name for product in products])))
        message = u"%s article(s) %s été %s." % (products_done_count, products_done_count == 1 and u'à' or u'ont',
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
    current_purchase_price = fields.Float(string=u"Coût actuel")
    new_purchase_price = fields.Float(string=u"Coût calculé")
