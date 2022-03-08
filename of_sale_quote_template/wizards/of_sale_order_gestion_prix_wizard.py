# -*- coding: utf-8 -*-

from odoo import api, fields, models


class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    calculation_basis = fields.Selection(selection=[
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
    def calculer(self, simuler=False):
        if self.calculation_basis == 'layout_category':
            lines_discountable = self.line_ids.filtered(lambda line: not line.product_forbidden_discount)

            # On prépare les lignes de commande du wizard pour le calcul
            categories_included = self.layout_category_ids.filtered(lambda line: line.state == 'included')
            order_lines_included = categories_included.mapped('order_line_ids').filtered(lambda sol: sol.price_unit)
            lines_included = lines_discountable.filtered(lambda line: line.order_line_id.id in order_lines_included.ids)

            # Pour les catégories forcées, on doit en plus calculer le prix total TTC simulé
            categories_forced = self.layout_category_ids.filtered(lambda line: line.state == 'forced')
            order_lines_forced = categories_forced.mapped('order_line_ids').filtered(lambda sol: sol.price_unit)
            lines_forced = lines_discountable.filtered(lambda line: line.order_line_id.id in order_lines_forced.ids)

            for category in categories_forced:
                category_price_forced = category.simulated_price_subtotal
                category_order_lines_forced = category.mapped('order_line_ids')
                category_lines_forced = lines_forced.filtered(
                    lambda line: line.order_line_id.id in category_order_lines_forced.ids)
                lines_forced_price = sum(category_lines_forced.mapped('prix_total_ht'))
                factor = category_price_forced / lines_forced_price if lines_forced_price else 1
                for lf in category_lines_forced:
                    lf.write({
                        'state': 'forced',
                        'prix_total_ht_simul': lf.prix_total_ht * factor,
                    })

            lines_excluded = self.line_ids - lines_included - lines_forced
            lines_included.write({'state': 'included'})
            lines_excluded.write({'state': 'excluded'})
            lines_forced.write({'state': 'forced'})

        super(GestionPrix, self).calculer(simuler)

        # On met à jour les informations dans les lignes de section du wizard
        for category in self.layout_category_ids:
            lines = self.line_ids.filtered(lambda line: line.order_line_id.id in category.order_line_ids.ids)

            # Dans le cas ou tous les états d'une catégorie sont identiques, on assigne cet état à la catégorie
            states = lines.mapped('state')
            if all(state == states[0] for state in states):
                category.state = states[0]
            elif 'included' in states:
                category.state = 'included'
            else:
                category.state = 'excluded'

            category.simulated_price_subtotal = sum(lines.mapped('prix_total_ht_simul'))
            category.simulated_price_total = sum(lines.mapped('prix_total_ttc_simul'))
            category.pc_sale_price = (category.simulated_price_subtotal / self.montant_total_ht_simul) * 100 \
                if self.montant_total_ht_simul else -100


class GestionPrixLayoutCategory(models.TransientModel):
    _name = 'of.sale.order.gestion.prix.layout.category'

    state = fields.Selection(
        selection=[('excluded', u"Exclus"), ('included', u"Inclus"), ('forced', u"Forcé")],
        string=u"État", required=True, default='included')
    wizard_id = fields.Many2one(comodel_name='of.sale.order.gestion.prix', required=True, ondelete='cascade')
    layout_category_id = fields.Many2one(
        comodel_name='of.sale.order.layout.category', string=u"Section", readonly=True, ondelete='cascade')
    order_line_ids = fields.Many2many(comodel_name='sale.order.line', string=u"Lignes de commande")
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

    @api.depends('order_line_ids')
    def _compute_price(self):
        for line in self:
            line.price_reduce_taxexcl = sum(line.order_line_ids.mapped('price_reduce_taxexcl'))
            line.price_reduce_taxinc = sum(line.order_line_ids.mapped('price_reduce_taxinc'))
            line.price_subtotal = sum(line.order_line_ids.mapped('price_subtotal'))
            line.price_total = sum(line.order_line_ids.mapped('price_total'))
            line.cost = sum(map(lambda sol: sol.purchase_price * sol.product_uom_qty, line.order_line_ids))

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
            # La marge ne peut pas être supérieure ou égale à 100%
            line.pc_margin = min(line.pc_margin, 99.99)
            if line.state == 'included':
                line.simulated_price_subtotal = line.cost / ((100 - line.pc_margin) / 100) \
                    if line.pc_margin != 100 else line.cost
                factor = line.simulated_price_subtotal / line.price_subtotal if line.price_subtotal else 1
                line.simulated_price_total = line.price_total * factor
