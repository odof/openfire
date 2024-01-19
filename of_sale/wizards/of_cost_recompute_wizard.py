# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFCostRecomputeWizard(models.TransientModel):
    _name = 'of.cost.recompute.wizard'

    @api.model
    def default_get(self, field_list=None):
        res = super(OFCostRecomputeWizard, self).default_get(field_list)
        # Suivant que la prise de rdv se fait depuis la fiche client ou une demande d'intervention
        if self._context.get('active_model', '') == 'sale.order':
            res['order_ids'] = self._context['active_ids']
        return res

    order_ids = fields.Many2many(comodel_name='sale.order', string=u"Commande(s) concernée(s)")
    cost_method = fields.Selection(
        selection=[
            ('of_theoretical_cost', u"Coût commercial"),
            ('standard_price', u"Coût d'inventaire"),
        ], string=u"Méthode de coût", required=True)
    exclude_zero = fields.Boolean(string=u"Exclure les lignes dont le coût est zéro")
    exclude_change_zero = fields.Boolean(string=u"Exclure les remplacement de coût par zéro")
    real_cost = fields.Boolean(string=u"Calculer au réel les lignes liées à un approvisionnement")
    brand_ids = fields.Many2many(comodel_name='of.product.brand', string=u"Marques à exclure")
    product_categ_ids = fields.Many2many(comodel_name='product.category', string=u"Catégories d'articles à exclure")

    @api.multi
    def recompute_cost(self):
        if self.order_ids:
            self._recompute_order_costs()

    @api.multi
    def _recompute_order_costs(self):
        order_lines = self.order_ids.mapped('order_line')
        if self.brand_ids:
            brand_ids = self.brand_ids._ids
            order_lines = order_lines.filtered(lambda r: r.product_id.brand_id.id not in brand_ids)
        if self.product_categ_ids:
            categ_ids = self.product_categ_ids._ids
            order_lines = order_lines.filtered(lambda r: r.product_id.categ_id.id not in categ_ids)
        if self.exclude_zero:
            order_lines = order_lines.filtered('purchase_price')
        self._handle_order_lines(order_lines)

    @api.multi
    def _handle_order_lines(self, order_lines):
        field_used = self.cost_method
        for line in order_lines:
            cost = line.product_id[field_used]
            if self.real_cost and line.procurement_ids:
                purchase_lines = line.procurement_ids.mapped('move_ids.move_orig_ids.purchase_line_id')
                purchase_lines |= line.procurement_ids.mapped('move_ids.purchase_line_id')
                purchase_qty = sum(purchase_lines.mapped('product_qty'))
                if purchase_qty:
                    purchase_price_subtotal = sum(purchase_lines.mapped('price_subtotal'))
                    purchase_unit_price = purchase_price_subtotal / purchase_qty if purchase_qty else 0.0
                    cost = purchase_unit_price * line.product_id.property_of_purchase_coeff
            if self.exclude_change_zero and not cost:
                continue
            line.purchase_price = cost
