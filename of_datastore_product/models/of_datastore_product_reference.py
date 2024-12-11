# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, api, models

from odoo.addons.of_datastore.models.of_datastore_model import DATASTORE_IND


class OFDatastoreProductReference(models.AbstractModel):
    _name = "of.datastore.product.reference"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("product_id", 0) < 0:
                vals["product_id"] = self._ds_handle_product_id(vals)
            if vals.get("product_tmpl_id", 0) < 0:
                vals["product_tmpl_id"] = self.env["product.product"].browse(vals["product_id"]).product_tmpl_id.id

            if vals.get("product_ids") and vals["product_ids"][0][2]:
                vals["product_ids"] = self._ds_handle_product_ids(vals)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("product_id", 0) < 0:
            vals["product_id"] = self._ds_handle_product_id(vals)

        if vals.get("product_tmpl_id", 0) < 0:
            vals["product_tmpl_id"] = self.env["product.product"].browse(vals["product_id"]).product_tmpl_id.id

        if vals.get("product_ids") and vals["product_ids"][0][2]:
            vals["product_ids"] = self._ds_handle_product_ids(vals)
        return super().write(vals)

    def _ds_handle_product_id(self, vals):
        """Get product_id and replace negative id with the corresponding product id from the datastore."""
        if vals["product_id"] < 0:
            # on va créer le product template et retourner la variante créée à la volée
            pp = self.env["product.product"].browse(vals["product_id"])
            ptpl = (
                self.env["product.template"]
                .browse(pp.product_tmpl_id.id)
                .with_context({"create_product": False})
                .of_ds_import()
            )
            # sur les lignes de commandes et de factures, l'uom est encore en négative
            # on va donc mettre celle qui vient du produit, une fois qu'il est crée
            # ajout pour les lignes de commandes
            if vals.get("product_uom"):
                vals["product_uom"] = ptpl.uom_id.id
            # ajout pour les lignes de factures
            if vals.get("product_uom_id"):
                vals["product_uom_id"] = ptpl.uom_id.id

            return ptpl.product_variant_id.id

        else:
            return vals["product_id"]

    def _ds_handle_product_ids(self, vals):
        """Get product_ids and replace negative ids with the corresponding product ids from the datastore."""
        res = []
        product_ids = vals["product_ids"][0][2]
        ds_products = self.env["product.product"].browse([pid for pid in product_ids if pid < 0])
        ds_products_tmpl = ds_products.mapped("product_tmpl_id")

        # On appelle of_ds_import() ici plutôt que dans le for pour éviter d'appeler trop souvent la
        # base centralisée
        products = ds_products_tmpl.with_context({"create_product": False}).of_ds_import()
        ds_products_dict = {p.of_datastore_res_id: p.product_variant_id for p in products}

        for pid in product_ids:
            if pid < 0:
                pid = ds_products_dict[-pid % DATASTORE_IND]
            res.append(pid)
        vals["product_ids"] = [Command.set[res]]
        return vals["product_ids"]
