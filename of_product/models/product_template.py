# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.of_utils.models.misc import is_valid_url


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_model = fields.Char(string="Model")
    of_manufacturer_description = fields.Text(string="Manufacturer Description", translate=True)
    of_cost_date = fields.Date(string="Cost date")

    # Retrait de la catégorie par défaut (avec possibilité d'héritage)
    categ_id = fields.Many2one(default=lambda self: self._get_default_category_id())
    # Retrait de la société par défaut
    company_id = fields.Many2one(default=False)

    # Ajout de la catégorie d'udm pour permettre de filtrer les udms d'achat autorisées
    of_uom_category_id = fields.Many2one(related="uom_id.category_id", readonly=True)
    uom_po_id = fields.Many2one(domain="[('category_id', '=', of_uom_category_id)]")
    # Ajout de champs copiés de l'udm de vente pour affichage
    of_uom_po_id_display = fields.Many2one(related="uom_po_id", string="Purchase UoM (display)", readonly=True)
    of_uom_po_id_display2 = fields.Many2one(related="uom_po_id", string="Purchase UoM (display 2)", readonly=True)

    # Champs ajoutés pour openImport et affichage dans formulaire produit
    of_seller_pp_untaxed = fields.Float(
        related="seller_ids.of_public_price_untaxed", related_sudo=False, store=True, readonly=False
    )
    of_seller_price = fields.Float(
        related="seller_ids.price", string="Purchase price", related_sudo=False, store=True, readonly=False
    )
    of_seller_discount = fields.Float(related="seller_ids.of_discount", related_sudo=False, store=True, readonly=False)
    of_seller_product_code = fields.Char(related="seller_ids.product_code", related_sudo=False)
    of_seller_product_name = fields.Char(related="seller_ids.product_name", related_sudo=False)
    of_seller_product_category_name = fields.Char(related="seller_ids.of_product_category_name", related_sudo=False)
    of_seller_delay = fields.Integer(related="seller_ids.delay")

    of_linked_product_ids = fields.Many2many(
        comodel_name="product.template",
        column1="of_product_template1_id",
        column2="of_product_template2_id",
        relation="linked_product_rel",
        string="Related products",
    )

    of_obsolete = fields.Boolean(string="Obsolete item")

    # Structure de prix
    of_purchase_transport = fields.Float(string="Transport on purchase")
    of_sale_transport = fields.Float(string="Transport on sale")
    of_sale_coeff = fields.Float(string="Sale coefficient")
    of_other_logistic_costs = fields.Float(string="Other logistics costs")
    of_misc_taxes = fields.Float(string="Miscellaneous taxes")
    of_misc_costs = fields.Float(string="Miscellaneous costs")
    of_url = fields.Char(string="URL")

    def _get_default_category_id(self):
        return False

    @api.onchange("of_seller_pp_untaxed")
    def onchange_of_seller_pp_untaxed(self):
        if self.seller_ids:
            self.seller_ids[0].of_public_price_untaxed = self.of_seller_pp_untaxed

    @api.onchange("of_seller_price")
    def onchange_of_seller_price(self):
        if self.seller_ids:
            self.seller_ids[0].price = self.of_seller_price

    @api.model_create_multi
    def create(self, vals_list):
        category_all = self.env.ref("product.product_category_all", raise_if_not_found=False)
        for vals in vals_list:
            if vals.get("of_url") and not is_valid_url(vals["of_url"]):
                raise UserError(_("The entered URL is not correct !"))

            if not vals.get("categ_id"):
                # if no category is given at creation (that sould not be possible from the backend interface because
                # its required), we are trying to find one from the context
                if (
                    categ_id := self._context.get("categ_id")
                    or self._context.get("default_categ_id")
                    or category_all
                    and category_all.id
                ):
                    vals["categ_id"] = categ_id
        if self._context.get("of_no_log"):
            # old V10 stuff to desactivate log creation for product creation (was usefull for import), but it now
            # driven by a context key to keep the possibility to log product creation if needed
            return super(ProductTemplate, self.with_context(mail_create_nolog=True)).create(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("of_url") and not is_valid_url(vals["of_url"]):
            raise UserError(_("The entered URL is not correct !"))
        return super().write(vals)
