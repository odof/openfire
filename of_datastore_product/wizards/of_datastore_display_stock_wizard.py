# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class OfDatastoreDisplayStock(models.TransientModel):
    _name = "of.datastore.display.stock"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get("active_ids") and self._context.get("active_model"):
            self._default_get_ds_values(res)
        return res

    qty_available = fields.Float()
    stock_informations = fields.Text()

    def _default_get_ds_values(self, res):
        product = self.env[self.env.context.get("active_model")].browse(self.env.context.get("active_ids")[0])
        if product.of_datastore_res_id and product.brand_id.datastore_supplier_id:
            supplier = product.brand_id.datastore_supplier_id
            try:
                client = supplier.of_datastore_connect()
                if isinstance(client, str):
                    res["stock_informations"] = _("Unable to connect to the product datastore.")
                    return res
                ds_product_obj = supplier.of_datastore_get_model(client, "product.template")
                qty_values = supplier.of_datastore_func(
                    ds_product_obj, "of_datastore_get_quantities", [product.of_datastore_res_id], []
                )
                res["qty_available"] = qty_values[0]
                res["stock_informations"] = qty_values[1]
            except Exception as e:
                # if we can't connect to the product datastore, we don't want to display an error
                # just don't display the stock information
                res["stock_informations"] = _("An error has occurred. (%(error_msg)s)", error_msg=e)
        return res
