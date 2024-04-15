# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, models

from .of_datastore_centralized import DATASTORE_IND


class OFDatastoreProductReference(models.AbstractModel):
    _name = "of.datastore.product.reference"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("product_id", 0) < 0:
                vals["product_id"] = self._ds_handle_product_id(vals)

            if vals.get("product_ids") and vals["product_ids"][0][2]:
                self._ds_handle_product_ids(vals)

        return super().create(vals_list)

    def write(self, vals):
        if vals.get("product_id", 0) < 0:
            vals["product_id"] = self._ds_handle_product_id(vals)

        if vals.get("product_ids") and vals["product_ids"][0][2]:
            self._ds_handle_product_ids(vals)
        return super().write(vals)

    def _ds_handle_product_id(self, vals):
        """Get product_id and replace negative id with the corresponding product id from the datastore."""
        if vals["product_id"] < 0:
            vals["product_id"] = self.env["product.product"].browse(vals["product_id"]).of_datastore_import().id

    def _ds_handle_product_ids(self, vals):
        """Get product_ids and replace negative ids with the corresponding product ids from the datastore."""
        res = []
        product_ids = vals["product_ids"][0][2]
        ds_products = self.env["product.product"].browse([pid for pid in product_ids if pid < 0])

        # On appelle of_datastore_import() ici plutôt que dans le for pour éviter d'appeler trop souvent la
        # base centralisée
        products = ds_products.of_datastore_import()
        ds_products_dict = {p.of_datastore_res_id: p.id for p in products}

        for pid in product_ids:
            if pid < 0:
                pid = ds_products_dict[-pid % DATASTORE_IND]
            res.append(pid)
        vals["product_ids"] = [Command.set[res]]
