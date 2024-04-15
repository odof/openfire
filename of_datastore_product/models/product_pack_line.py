#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

from .of_datastore_centralized import DATASTORE_IND


class ProductPackLine(models.Model):
    _name = "product.pack.line"
    _inherit = ["product.pack.line", "of.datastore.product.reference"]

    def read(self, fields=None, load="_classic_read"):
        real_records = self.filtered(lambda o: o.id > 0)

        res = super().read(fields, load=load)
        if ds_records := self - real_records:
            res += ds_records._of_read_datastore(fields)
        return res

    def _of_read_datastore(self, fields_to_read, create_mode=False):
        """Reads kit data from supplier database.

        Args:
            fields_to_read (list): List of fields to read.
            create_mode (bool): If True, create missing records.

        Returns:
            list: List of dictionaries containing the retrieved data.

        Notes: `self` contains modified pack lines ids in negative values.
        """
        supplier_obj = self.env["of.datastore.supplier"]
        brand_obj = self.env["of.product.brand"]
        product_obj = self.env["product.product"]
        res = []

        # Kits par fournisseur
        datastore_kit_ids = {}
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_kit_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        for supplier in supplier_obj.browse(datastore_kit_ids):
            client = supplier.of_datastore_connect()
            ds_pack_obj = supplier.of_datastore_get_model(client, "product.pack.line")

            # Données de la base fournisseur
            packs_data = supplier.of_datastore_read(ds_pack_obj, datastore_kit_ids[supplier.id], [])
            ds_product_ids = [pack["product_id"][0] for pack in packs_data]

            # Détection des composants du kit déjà importés
            # Attention de bien détecter les articles archivés (pourrait sinon provoquer des erreurs lors de l'import)
            products = product_obj.with_context(active_test=False).search(
                [("brand_id", "in", supplier.brand_ids.ids), ("of_datastore_res_id", "in", ds_product_ids)]
            )

            product_match = {product.of_datastore_res_id: product.id for product in products}
            product_names = dict(products.name_get())

            # Affectation des ids des champs relationnels
            supplier_value = supplier.id * DATASTORE_IND
            match_dicts = {}
            for pack in packs_data:
                # Articles
                product_id, product_name = pack["product_id"]
                if product_id in product_match:
                    # Composant déjà importé
                    product_id = product_match[product_id]
                    product_name = product_names[product_id]
                else:
                    # Composant virtuel
                    product_id = -(product_id + supplier_value)
                pack["product_id"] = (product_id, product_name)
                pack["id"] = -(pack["id"] + supplier_value)

                # Unités de mesure
                uom_id, uom_name = pack["product_uom_id"]
                uom_id = brand_obj.datastore_match(
                    client, "product.uom", uom_id, uom_name, False, match_dicts, create=create_mode
                ).id
                pack["product_uom_id"] = (uom_id, uom_name)
            res += packs_data
        return res
