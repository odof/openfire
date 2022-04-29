# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    calculation_basis = fields.Selection(
        selection=[
            ('order_line', u"Articles"),
            ('layout_category', u"Sections")
        ], string=u"Base de calcul", required=True, default='order_line')
    layout_category_ids = fields.One2many(
        comodel_name='of.sale.order.gestion.prix.layout.category',
        inverse_name='wizard_id', string=u'Sections impactées')

    @api.multi
    def bouton_inclure_tout(self):
        super(GestionPrix, self).bouton_inclure_tout()
        self.layout_category_ids.write({'state': 'included'})

    @api.multi
    def bouton_exclure_tout(self):
        super(GestionPrix, self).bouton_exclure_tout()
        self.layout_category_ids.write({'state': 'excluded'})

    @api.multi
    def _calculer(self, total, mode, currency, line_rounding):
        if self.calculation_basis != 'layout_category':
            return super(GestionPrix, self)._calculer(total, mode, currency, line_rounding)
        values = {}
        # Si on fonctionne par section, il n'y a pas de montant forcé par ligne de commande
        self.line_ids.filtered(lambda l: not l.state == 'included' and not l.product_forbidden_discount)\
            .write({'state': 'included'})

        price_field = 'simulated_price_subtotal' if mode == 'ht' else 'simulated_price_total'
        for category in self.layout_category_ids.filtered(lambda categ: categ.state != 'included'):
            if category.state == 'forced':
                values.update(
                    category.line_ids.distribute_amount(
                        category.simulated_price_subtotal, 'ht', currency, line_rounding))
            else:
                for line in category.line_ids:
                    line.prix_total_ht_simul = line.order_line_id.price_subtotal
                    line.prix_total_ttc_simul = line.order_line_id.price_total

            category.simulated_price_subtotal = sum(category.line_ids.mapped('prix_total_ht_simul'))
            category.simulated_price_total = sum(category.line_ids.mapped('prix_total_ttc_simul'))
            total -= category[price_field]
        if total < 0:
            raise UserError(u"(Erreur #RG405)\nLe montant forcé dépasse le montant total à distribuer")

        included_categories = self.layout_category_ids.filtered(lambda categ: categ.state == 'included')
        values.update(
            included_categories.mapped('line_ids').distribute_amount(total, mode, currency, line_rounding)
        )
        for category in included_categories:
            category.write({
                'simulated_price_subtotal': sum(category.line_ids.mapped('prix_total_ht_simul')),
                'simulated_price_total': sum(category.line_ids.mapped('prix_total_ttc_simul')),
            })
        return values


class GestionPrixLayoutCategory(models.TransientModel):
    _name = 'of.sale.order.gestion.prix.layout.category'

    state = fields.Selection(
        selection=[('excluded', u"Exclus"), ('included', u"Inclus"), ('forced', u"Forcé")],
        string=u"État", required=True, default='included')
    wizard_id = fields.Many2one(comodel_name='of.sale.order.gestion.prix', required=True, ondelete='cascade')
    layout_category_id = fields.Many2one(
        comodel_name='of.sale.order.layout.category', string=u"Section", readonly=True, ondelete='cascade')
    line_ids = fields.Many2many(
        comodel_name='of.sale.order.gestion.prix.line',
        relation='of_sale_order_gestion_prix_layout_category_line_rel',
        string=u"Lignes impactées")
    currency_id = fields.Many2one(related='layout_category_id.currency_id')

    cost = fields.Float(string=u"Coût", compute='_compute_price')
    pc_sale_price = fields.Float(string=u"% Prix de vente", readonly=True)

    price_reduce_taxexcl = fields.Monetary(string=u"Prix unit. HT initial", compute='_compute_price')
    price_reduce_taxinc = fields.Monetary(string=u"Prix unit. TTC initial", compute='_compute_price')
    price_subtotal = fields.Monetary(string=u"Prix total HT initial", compute='_compute_price')
    price_total = fields.Monetary(string=u"Prix total TTC initial", compute='_compute_price')
    simulated_price_subtotal = fields.Float(string=u"Prix total HT simulé")
    simulated_price_total = fields.Float(string=u"Prix total TTC simulé", readonly=True)

    margin = fields.Float(string=u"Marge HT", compute='_compute_marge')
    pc_margin = fields.Float(string=u"% Marge", compute='_compute_marge')

    of_client_view = fields.Boolean(string=u"Vue client/vendeur", related="wizard_id.of_client_view")

    @api.depends('line_ids')
    def _compute_price(self):
        for categ in self:
            order_lines = categ.line_ids.mapped('order_line_id')
            categ.price_reduce_taxexcl = sum(order_lines.mapped('price_reduce_taxexcl'))
            categ.price_reduce_taxinc = sum(order_lines.mapped('price_reduce_taxinc'))
            categ.price_subtotal = sum(order_lines.mapped('price_subtotal'))
            categ.price_total = sum(order_lines.mapped('price_total'))
            categ.cost = sum(sol.purchase_price * sol.product_uom_qty for sol in order_lines)

    @api.depends('cost', 'simulated_price_subtotal')
    def _compute_marge(self):
        for line in self:
            buy_price = line.cost
            sell_price = line.simulated_price_subtotal

            line.margin = sell_price - buy_price
            line.pc_margin = 100 * (1 - buy_price / sell_price) if sell_price else - buy_price

    @api.onchange('pc_margin')
    def _onchange_pc_margin(self):
        for line in self:
            # La marge ne peut pas être supérieure ou égale à 100%, sauf si le cout est nul
            if line.cost == 0:
                pc_margin_max = 100
            else:
                pc_margin_max = 99.99
            if line.pc_margin > pc_margin_max:
                line.pc_margin = pc_margin_max

            pc_margin = 100 * (1 - line.cost / line.simulated_price_subtotal) if line.simulated_price_subtotal else -100
            if float_compare(pc_margin, line.pc_margin, precision_rounding=0.01):
                line.simulated_price_subtotal = line.cost and line.cost * (100 / (100 - line.pc_margin))
                factor = line.simulated_price_subtotal / line.price_subtotal if line.price_subtotal else 1
                line.simulated_price_total = line.price_total * factor
