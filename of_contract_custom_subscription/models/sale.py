# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# 1: imports of python lib
from datetime import datetime
from dateutil.relativedelta import relativedelta
# 2: imports of odoo
from odoo import models, fields, api
from odoo.exceptions import UserError
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib

# 1: imports of python lib
# 2: imports of odoo
# 3: imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_contract_template_id = fields.Many2one(comodel_name='of.contract.template', string=u"Modèle de contrat")
    of_contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat")
    of_subscription = fields.Boolean(string="Facturation par abonnement", compute='_compute_of_subscription')

    @api.depends('order_line.product_id.of_subscription')
    def _compute_of_subscription(self):
        for order in self:
            order.of_subscription = any(order.order_line.mapped('of_subscription'))

    def get_contract_vals(self):
        self.ensure_one()
        if not self.of_contract_template_id:
            raise UserError(u"Vous devez définir un modèle de contrat pour continuer.")
        template_vals = self.of_contract_template_id.template_to_record_vals()
        template_vals.update({
            'partner_id': self.partner_id.id,
            'date_souscription': fields.Date.today(),
            'analytic_account_id': self.related_project_id.id
        })
        return template_vals

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.of_subscription and not self.of_contract_id:
                contract_vals = order.get_contract_vals()
                contract_lines = []
                for order_line in order.order_line.filtered('of_subscription'):
                    contract_lines.append((0, 0, order_line.get_contract_vals()))
                contract_vals.update({
                    'line_ids': contract_lines,
                })
                contract = self.env['of.contract'].create(contract_vals)
                contract.line_ids.mapped('contract_product_ids')._compute_tax_id()
                order.write({'of_contract_id': contract.id})
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_subscription = fields.Boolean(string="Facturation par abonnement")
    of_contract_line_template_id = fields.Many2one(
        comodel_name='of.contract.line.template', string=u"Modèle ligne de contrat")
    of_date_mis = fields.Date(string="Date mise en service")
    of_contract_line_id = fields.One2many(
        comodel_name='of.contract.line', inverse_name='order_line_id', string="Lignes de contrat")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            self.of_subscription = self.product_id.of_subscription
        return res

    @api.onchange('of_contract_line_template_id')
    def _onchange_of_contract_line_template_id(self):
        if self.of_contract_line_template_id:
            template = self.of_contract_line_template_id
            date = fields.Date.to_string(datetime.today() + relativedelta(day=template.jour_debut,
                                                                          month=template.mois_id.numero))
            self.of_date_mis = date

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy',
                 'of_subscription')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self.filtered('of_subscription'):
            line.qty_to_invoice = 0  # est facturée par contrat
        super(SaleOrderLine, self.filtered(lambda l: not l.of_subscription))._get_to_invoice_qty()

    def get_contract_vals(self):
        self.ensure_one()
        if not self.of_contract_line_template_id:
            raise UserError(u"Vous devez définir un modèle de line de contrat pour continuer."
                            u"Ligne de commande %s" % self.name)
        template_vals = self.of_contract_line_template_id.template_to_record_vals()
        contract_product_obj = self.env['of.contract.product']
        new_contract_product = contract_product_obj.new({'product_id': self.product_id.id})
        new_contract_product._onchange_product_id()
        new_contract_product.update({
            'price_unit': self.price_unit,
        })
        template_vals.update({
            'contract_product_ids': template_vals.get('contract_product_ids', []) +
                                    [(0, 0, new_contract_product._convert_to_write(new_contract_product._cache))],
            'order_line_id': self.id,
            'date_start': self.of_date_mis,
            'address_id': self.order_id.partner_shipping_id.id,
        })
        return template_vals
