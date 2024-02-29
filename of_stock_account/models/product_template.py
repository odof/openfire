# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_margin = fields.Float(
        string="Margin",
        digits=(4, 2),
        compute='_compute_of_margin',
        help="Margin calculated on the basis of the sale price",
    )
    of_theoretical_cost = fields.Float(
        string="Theoretical cost",
        compute='_compute_of_theoretical_cost',
        inverse='_inverse_set_of_theoretical_cost',
        search='_search_of_theoretical_cost',
        digits='Product Price',
        groups='base.group_user',
        help="Corresponds to the cost calculated by applying the rules defined in the brand or in the import files. "
        "This cost value can be used for margin calculation in quotes and invoices; however, it is never used for "
        "inventory valuation.",
    )
    # Uniformisation de la méthode de coût sur les sociétés (effectif si of_base_multicompany est installé)
    # Normalement inutile car la modification de cette valeur est inhibée par Odoo (cf commit af9d21b3) pour préférer
    # une gestion directement depuis les catégories d'articles
    cost_method = fields.Selection(of_unify_companies=True)

    # ---------------------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------------------

    @api.depends('product_variant_ids', 'product_variant_ids.of_theoretical_cost')
    def _compute_of_theoretical_cost(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.of_theoretical_cost = template.product_variant_ids.of_theoretical_cost
        for template in self - unique_variants:
            template.of_theoretical_cost = 0.0

    def _inverse_set_of_theoretical_cost(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.of_theoretical_cost = template.of_theoretical_cost
                # On répercute le changement sur le coût standard
                if template.cost_method == 'standard':
                    template.product_variant_ids.standard_price = template.of_theoretical_cost

    def _search_of_theoretical_cost(self, operator, value):
        products = self.env['product.product'].search([('of_theoretical_cost', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]

    def _set_standard_price(self):
        super()._set_standard_price()
        # On répercute le changement sur le coût théorique
        for template in self:
            if len(template.product_variant_ids) == 1 and template.cost_method == 'standard':
                template.product_variant_ids.of_theoretical_cost = template.standard_price

    @api.depends('list_price', 'standard_price', 'of_theoretical_cost')
    def _compute_of_margin(self):
        # la marge est calculée en fonction du prix de vente, faire en fonction du prix d'achat?
        for product in self:
            list_price = product.list_price
            if list_price != 0:
                product.of_margin = (list_price - product.get_cost()) * 100.00 / list_price
            else:  # division par 0!
                product.of_margin = 0

    # ---------------------------------------------------------------------------
    # CRUD methods
    # ---------------------------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == 'of_unify_companies' or super()._valid_field_parameter(field, name)

    # ---------------------------------------------------------------------------
    # Business methods
    # ---------------------------------------------------------------------------

    def get_cost(self):
        self.ensure_one()
        if self.cost_method == 'standard' or self.categ_id.of_sale_cost == 'standard':
            return self.standard_price
        else:
            return self.of_theoretical_cost

    def _get_related_fields_variant_template(self):
        related_fields = super()._get_related_fields_variant_template()
        related_fields.append('of_theoretical_cost')
        return related_fields
