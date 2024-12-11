# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models

from odoo.addons.of_datastore.models.of_datastore_model import DATASTORE_IND


class OFDatastoreSupplierBrand(models.AbstractModel):
    _name = "of.datastore.supplier.brand"

    name = fields.Char(string="Supplier brand", required=True, readonly=True)
    datastore_brand_id = fields.Integer(string="Supplier brand ID", required=True, readonly=True)
    brand_id = fields.Many2one(comodel_name="of.product.brand", string="Brand")
    product_count = fields.Integer(string="# Products", readonly=True)
    price_date = fields.Date(readonly=True)
    update_note = fields.Text(string="Update notes", readonly=True)
    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def read(self, fields=None, load="_classic_read"):
        """
        Read method to retrieve data from the datastore supplier brand.

        Args:
            fields (list, optional): List of fields to retrieve. Defaults to None.
            load (str, optional): Load type. Defaults to '_classic_read'.

        Returns:
            list: List of dictionaries containing the retrieved data.
        """
        brand_obj = self.env["of.product.brand"]
        ds_supplier_obj = self.env["of.datastore.supplier"]
        default_ds_brand_name = _("Error")
        result = []
        for ds_brand_full_id in self.ids:
            ds_supplier_id = ds_brand_full_id // DATASTORE_IND
            ds_brand_id = ds_brand_full_id % DATASTORE_IND

            brand = brand_obj.search(
                [("datastore_supplier_id", "=", ds_supplier_id), ("datastore_brand_id", "=", ds_brand_id)], limit=1
            )

            if brand:
                brand_id = (brand.id, brand.name)
            else:
                brand_id = False

            vals = {
                "id": ds_brand_full_id,
                "brand_id": brand_id,
                "name": default_ds_brand_name,
                "datastore_brand_id": False,
                "update_date": False,
                "update_note": "",
                "product_count": False,
            }

            ds_supplier = ds_supplier_obj.browse(ds_supplier_id)
            client = ds_supplier.of_datastore_connect()
            if not isinstance(client, str):
                ds_brand_obj = ds_supplier.of_datastore_get_model(client, "of.product.brand")
                ds_brand_data = ds_supplier.of_datastore_read(
                    ds_brand_obj, [ds_brand_id], ["name", "price_date", "update_note", "product_count", "display_name"]
                )[0]
                del ds_brand_data["id"]
                vals.update(ds_brand_data)

            if fields:
                if "id" not in fields:
                    fields.append("id")
                vals = {key: val for key, val in iter(vals.items()) if key in fields}

            result.append(vals)

        return result

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if args and len(args) == 1 and args[0][0] == "id":
            return args[0][2]
        return super()._search(args, offset, limit, order, count, access_rights_uid)

    def write(self, vals):
        if self and vals and "brand_id" in vals:
            brand_obj = self.env["of.product.brand"]
            ds_brand_full_id = self.ids[0]
            ds_supplier_id = ds_brand_full_id // DATASTORE_IND
            ds_brand_id = ds_brand_full_id % DATASTORE_IND

            new_brand_id = vals["brand_id"]
            old_brand = brand_obj.search(
                [("datastore_supplier_id", "=", ds_supplier_id), ("datastore_brand_id", "=", ds_brand_id)]
            )
            if new_brand_id == old_brand.id:
                return True
            if old_brand:
                self._ds_handle_brand_update(old_brand, False, False)
            if new_brand_id:
                new_brand = brand_obj.browse(new_brand_id)
                self._ds_handle_brand_update(new_brand, ds_supplier_id, ds_brand_id)

            # Mis à jour des demandes de connexion de prix centralisés
            self._update_product_datastore_connection_requests(ds_supplier_id, new_brand_id, ds_brand_id)
        return True

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _ds_handle_brand_update(self, brand, ds_supplier_id, ds_brand_id):
        brand.write({"datastore_supplier_id": ds_supplier_id, "datastore_brand_id": ds_brand_id})
        # On vide le champ of_datastore_res_id des articles de la marque qui n'est plus liée au TC
        # ou qui est nouvellement liée.
        brand.product_ids.write({"of_datastore_res_id": False})
        brand.product_variant_ids.write({"of_datastore_res_id": False})

    def _update_product_datastore_connection_requests(self, ds_supplier_id, new_brand_id, ds_brand_id):
        """
        Updates the centralized product datastore connection requests for a given supplier and brand.

        This method updates the connection requests for a supplier's brand in the datastore.
        If a new brand ID is provided, the brand is marked as connected with the new brand ID.
        If no new brand ID is provided, the brand is marked as available.

        Args:
            ds_supplier_id (int): The ID of the supplier in the datastore.
            new_brand_id (int): The new brand ID to be associated with the supplier.
            ds_brand_id (int): The ID of the brand in the datastore.

        Returns:
            None
        """
        supplier = self.env["of.datastore.supplier"].browse(ds_supplier_id)
        if datastore_brand := self.env["of.datastore.brand"].search(
            [("db_name", "=", supplier.db_name), ("datastore_brand_id", "=", ds_brand_id)]
        ):
            if new_brand_id:
                datastore_brand.write({"brand_id": new_brand_id, "state": "connected"})
            else:
                datastore_brand.write({"brand_id": False, "state": "available"})
