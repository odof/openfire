# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def _of_is_quantity_dependent(self, product_id, date_eval=None):
        """Check if the pricelist is quantity dependent for the given product and date
        :param product_id: ID of the product
        :param date_eval: Date to evaluate the pricelist on (default: today)
        :return: True if the pricelist is quantity dependent for the given product and date
        """
        self.ensure_one()
        if date_eval is None:
            date_eval = fields.Date.today()
        product = self.env['product.product'].browse(product_id)
        for item in self.item_ids:
            if item.min_quantity and item.min_quantity > 1:
                # une date de début pour cet item et la date d'évaluation antérieure à cette date de début
                if item.date_start and date_eval < item.date_start:
                    continue
                # une date de fin pour cet item et la date d'évaluation postérieure à cette date de fin
                if item.date_end and date_eval > item.date_end:
                    continue
                # l'item s'applique sur une catégorie d'article différente de celle de l'article évalué
                if (
                    item.applied_on == '2_product_category'
                    and item.categ_id
                    and item.categ_id != product.product_tmpl_id.categ_id
                ):
                    continue
                # l'item s'applique sur un article différent de l'article évalué
                if (
                    item.applied_on == '1_product'
                    and item.product_tmpl_id
                    and item.product_tmpl_id != product.product_tmpl_id
                ):
                    continue
                # l'item s'applique sur une variante différente de la variante évaluée
                if item.applied_on == '0_product_variant' and item.product_id and item.product_id != product:
                    continue
                return True
        return False
