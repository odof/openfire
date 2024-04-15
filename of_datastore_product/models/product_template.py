# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextlib import suppress

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .of_datastore_centralized import DATASTORE_IND


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "of.datastore.centralized"]

    of_datastore_supplier_id = fields.Many2one(
        comodel_name="of.datastore.supplier",
        related="brand_id.datastore_supplier_id",
        help="This field is used to search on the product datastore.",
    )
    of_datastore_has_link = fields.Boolean(compute="_compute_of_datastore_has_link")
    of_next_price_list = fields.Float(string="Next price list", digits="Product Price", default=0.0, readonly=True)
    of_next_price_list_date = fields.Date(string="Next price list date", readonly=True)
    of_display_supplier_stock_button = fields.Boolean(
        string="Centralized stock", compute="_compute_of_display_supplier_stock_button", store=True
    )

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    def _compute_of_datastore_has_link(self):
        for product in self:
            product.of_datastore_has_link = False

    @api.depends("of_datastore_res_id")
    def _compute_of_display_supplier_stock_button(self):
        for product in self:
            if product.of_datastore_res_id and product.brand_id.datastore_supplier_id:
                brand = product.brand_id
                supplier = brand.datastore_supplier_id

                with suppress(Exception):
                    client = supplier.of_datastore_connect()
                    if isinstance(client, str):
                        continue

                    ds_brand_obj = supplier.of_datastore_get_model(client, "of.product.brand")
                    can_read = supplier.of_datastore_func(
                        ds_brand_obj, "of_access_stocks", [brand.datastore_brand_id], []
                    )
                    product.of_display_supplier_stock_button = can_read

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        name, brands = self.of_name_search_extract_brands(name)
        new_args = args
        if brands:
            new_args = [("brand_id", "in", brands._ids)] + list(args or [])
        res = super().name_search(name, new_args, operator, limit)
        res = self._of_datastore_name_search(res, brands, name, args, operator, limit)
        return res

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        if field_name in ("default_code", "standard_price"):
            return False
        return super()._of_datastore_is_computed_field(field_name)

    def of_datastore_import(self):
        """
        Import products from the central database using the OpenFire Datastore.

        This method connects to the central database, retrieves the products associated with the suppliers,
        and imports them into the local database.

        Returns:
            product_tmpl_ids (recordset): The product template IDs of the imported products.
        """
        supplier_obj = self.env["of.datastore.supplier"]

        # Produits par fournisseur
        datastore_product_ids = {}
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_product_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        product_ids = []
        for supplier in supplier_obj.browse(datastore_product_ids.keys()):
            supplier_value = supplier.id * DATASTORE_IND
            client = supplier.of_datastore_connect()
            if isinstance(client, str):
                raise ValidationError(_("Connection error to central database %(dbname)s", dbname=supplier.name))

            product_obj = supplier_obj.of_datastore_get_model(client, "product.product")
            product_ids += [
                -(product_id + supplier_value)
                for product_id in supplier_obj.of_datastore_search(
                    product_obj, [("product_tmpl_id", "in", datastore_product_ids[supplier.id])]
                )
            ]

        return self.env["product.product"].browse(product_ids).of_datastore_import().mapped("product_tmpl_id")
