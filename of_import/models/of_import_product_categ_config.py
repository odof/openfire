# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfImportProductCategConfig(models.Model):
    _name = 'of.import.product.categ.config'
    _inherit = 'of.import.product.config.template'
    _order = 'categ_origin'

    brand_id = fields.Many2one(comodel_name='of.product.brand', required=True, string="Brand")
    categ_origin = fields.Char(string="Origin Category", required=True)
    product_ids = fields.One2many(comodel_name='product.template', string="Products", compute='_compute_product_ids')

    @api.depends('categ_origin', 'brand_id.product_ids', 'brand_id.product_ids.of_seller_product_category_name')
    def _compute_product_ids(self):
        product_obj = self.env['product.template']
        for categ in self:
            categ.product_ids = product_obj.search(
                [('brand_id', '=', categ.brand_id.id), ('seller_ids.of_product_category_name', '=', categ.categ_origin)]
            )

    _sql_constraints = [
        ('categ_origin_uniq', 'unique(brand_id, categ_origin)', "A product category can only be entered once."),
    ]

    def action_button_update_products(self):
        """
        Recalcule les champs des articles en fonction de la configuration de la marque
        et des paramètres d'import de l'article (dans product_supplierinfo)
        """
        self.mapped('product_ids').action_button_update_from_brand()
