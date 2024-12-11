# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import contextlib

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.of_datastore.models.of_datastore_cache import DS_CACHE
from odoo.addons.of_datastore.models.of_datastore_model import DATASTORE_IND


class OFProductBrand(models.Model):
    _inherit = "of.product.brand"

    datastore_supplier_id = fields.Many2one(comodel_name="of.datastore.supplier", string="Product datastore connector")
    datastore_brand_id = fields.Integer(string="Centralized ID")
    datastore_update_date = fields.Date(string="Update date", related="datastore_brand_request_ids.update_date")

    datastore_note_update = fields.Text(string="Update notes", compute="_compute_datastore_note_update")
    datastore_product_count = fields.Integer(
        string="# Products (PD)", compute="_compute_datastore_note_update", help="The number of products of this brand"
    )

    datastore_brand_request_ids = fields.One2many(
        comodel_name="of.datastore.brand", inverse_name="brand_id", string="PD brand request"
    )
    datastore_brand_request_id = fields.Many2one(
        comodel_name="of.datastore.brand",
        compute="_compute_datastore_brand_request_id",
        store=True,
        string="PD brand request (last)",
    )
    datastore_brand_request_state = fields.Selection(related="datastore_brand_request_id.state")
    datastore_update_required = fields.Boolean(
        string="To update", compute="_compute_datastore_update_required", search="_search_datastore_update_required"
    )

    def of_ds_match_many2one(self, value, base_index, data):
        base_id = base_index // DATASTORE_IND
        brand = self.env["of.product.brand"].search(
            [("datastore_brand_id", "=", value[0]), ("datastore_supplier_id", "=", base_id)], limit=1
        )
        if brand:
            return (brand.id, brand.name)
        # on retourne un id négatif basé sur l'index de la base distante
        brand = self.browse(-(value[0] + base_index))
        return (brand.id, brand.name)

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("datastore_brand_request_ids")
    def _compute_datastore_brand_request_id(self):
        for brand in self:
            brand.datastore_brand_request_id = brand.datastore_brand_request_ids

    @api.depends("price_date", "datastore_brand_request_id.state", "datastore_brand_request_ids.update_date")
    def _compute_datastore_update_required(self):
        for brand in self:
            brand.datastore_update_required = (
                brand.datastore_brand_request_state == "connected"
                and brand.datastore_update_date
                and brand.price_date < brand.datastore_update_date
            )

    @api.model
    def _search_datastore_update_required(self, operator, value):
        """
        A brand needs an update if it doesn't have at least one item on the price list update date.
        For this search, we exclude items created after this update date.
        """
        op = "in" if (operator == "=") == value else "not in"
        self.env.cr.execute(
            "SELECT brand.id "
            "FROM of_product_brand AS brand "
            "  INNER JOIN of_datastore_brand AS ds_brand ON ds_brand.brand_id = brand.id "
            "  INNER JOIN product_template AS tmpl "
            "    ON tmpl.brand_id = brand.id AND tmpl.create_date < ds_brand.update_date "
            "WHERE brand.datastore_brand_id IS NOT NULL "
            "GROUP BY brand.id, ds_brand.id "
            "HAVING MAX(tmpl.date_tarif) < ds_brand.update_date"
        )
        brand_ids = [row[0] for row in self.env.cr.fetchall()]
        return [("id", op, brand_ids)]

    @api.depends("datastore_supplier_id")
    def _compute_datastore_note_update(self):
        suppliers_brands = {}

        # Regroupement des marques par base centrale
        for brand in self:
            if brand.datastore_supplier_id:
                suppliers_brands.setdefault(brand.datastore_supplier_id, []).append(brand.datastore_brand_id)

        suppliers_data = {}
        for supplier, brand_ids in suppliers_brands.items():
            client = supplier.of_datastore_connect()
            if isinstance(client, str):
                suppliers_data[supplier] = _("Failed to connect to central base\n\n%(customer)s", customer=client)
                continue
            ds_brand_obj = supplier.of_datastore_get_model(client, "of.product.brand")
            ds_brand_ids = supplier.of_datastore_search(ds_brand_obj, [("id", "in", brand_ids)])
            suppliers_data[supplier] = {
                data["id"]: (data["update_note"], data["product_count"])
                for data in supplier.of_datastore_read(ds_brand_obj, ds_brand_ids, ["update_note", "product_count"])
            }

        for brand in self:
            product_count = 0
            if not brand.datastore_supplier_id:
                note = _("Brand not associated with a central database")
            elif isinstance(suppliers_data[brand.datastore_supplier_id], str):
                note = suppliers_data[brand.datastore_supplier_id]
            elif brand.datastore_brand_id not in suppliers_data[brand.datastore_supplier_id]:
                note = _("Brand not present on central database")
            else:
                note, product_count = suppliers_data[brand.datastore_supplier_id][brand.datastore_brand_id]
            brand.datastore_note_update = note
            brand.datastore_product_count = product_count

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def read(self, fields=None, load="_classic_read"):
        if self._context.get("of_datastore_update_categ") and fields and "categ_ids" in fields:
            self._ds_handle_brands_categories()
        return super().read(fields, load=load)

    def write(self, vals):
        # Autorise l'ajout de règles pour des articles centralisés
        new_products = False
        if vals.get("product_config_ids", False):
            vals["product_config_ids"], new_products = self._datastore_update_product_vals(vals["product_config_ids"])

        res = super().write(vals)

        # Lors de la modification de la marque, les données en cache sont invalidées
        if vals and self and not self._context.get("no_clear_datastore_cache"):
            DS_CACHE.clear_cache(self.env.cr.dbname)
        if new_products:
            new_products.action_button_update_from_brand()
        return res

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def datastore_match(self, client, obj, res_id, res_name, product, match_dicts, create=True):
        """
        Matches and retrieves data from the datastore based on the provided parameters.

        Args:
            client (str): The client identifier.
            obj (str): The name of the object to match.
            res_id (int): The ID of the resource to match.
            res_name (str): The name of the resource to match.
            product (product.product): The product to match.
            match_dicts (dict): A dictionary containing the precalculated match results.
            create (bool, optional): A flag indicating whether to create a new record if no match is found.
                Defaults to True.

        Returns:
            object: The matched record from the datastore.

        Raises:
            ValidationError: If the UDM category does not exist.

        Note:
            This method performs matching and retrieval of data from the datastore based on the provided parameters.
            It handles specific cases for different objects and uses precalculated match results for optimization.
            If no match is found and the `create` flag is set to True, it creates a new record.
        """

        def datastore_matching_model(obj_name, obj_id):
            """
            Tests if a match exists in the ir_model_data table
            Note: This way of doing things is dangerous because the elements could have been modified by hand,
                    only use it for rare models.
            """
            model_ids = ds_supplier_obj.of_datastore_search(
                ds_model_obj, [("model", "=", obj_name), ("res_id", "=", obj_id)]
            )
            if not model_ids:
                return self.env[obj_name]
            model = ds_supplier_obj.of_datastore_read(ds_model_obj, model_ids, ["module", "name"])[0]
            res_id = model_obj.search([("module", "=", model["module"]), ("name", "=", model["name"])]).res_id
            # Dans certains cas, un objet a pu être supprimé en DB mais pas sa référence dans ir_model_data
            return self.env[obj_name].search([("id", "=", res_id)])

        # --- Gestion des cas particuliers ---
        if obj == self._name:
            return self
        if obj == "product.category":
            return self.compute_product_categ(res_name, product)

        match_dict = match_dicts.setdefault(obj, {})

        # Recherche de correspondance dans les valeurs précalculées
        if res_id in match_dict:
            return match_dict[res_id]

        # Recherche de correspondance dans les identifiants externes (ir_model_data)
        model_obj = self.env["ir.model.data"]
        ds_supplier_obj = self.env["of.datastore.supplier"]
        ds_model_obj = ds_supplier_obj.of_datastore_get_model(client, "ir.model.data")
        ds_obj_obj = ds_supplier_obj.of_datastore_get_model(client, obj)
        result = False

        # Calcul de correspondance en fonction de l'objet
        obj_obj = self.env[obj]
        if obj == "product.template":
            if product:
                result = product
            else:
                # Ajouter un search par article est couteux.
                # Tant pis pour les règles d'accès, on fait une recherche SQL
                self._cr.execute(
                    "SELECT id FROM product_template WHERE brand_id = %s AND of_datastore_res_id = %s",
                    (self.id, res_id),
                )
                result = self._cr.fetchall()
                if result:
                    result = obj_obj.browse(result[0][0])
                else:
                    if create:
                        result = False
                    else:
                        # product_tmpl_id ne doit pas etre False,
                        # notamment a cause de la fonction pricelist.price_get_multi qui genererait une erreur
                        # Pour eviter des effets de bord, on met une valeur negative
                        result = obj_obj.browse(-(res_id + self.datastore_supplier_id.id * DATASTORE_IND))
        elif obj == "product.uom.categ":
            result = datastore_matching_model(obj, res_id)
            if not result:
                result = obj_obj.search([("name", "=", res_name)], limit=1)
                if not result:
                    raise ValidationError(_("UDM category non-existent : ") + res_name)
        elif obj == "product.uom":
            # Etape 1 : Déterminer la catégorie d'udm
            ds_obj = ds_supplier_obj.of_datastore_read(
                ds_obj_obj, [res_id], ["category_id", "factor", "uom_type", "rounding"]
            )[0]

            categ = self.datastore_match(
                client, "product.uom.categ", ds_obj["category_id"][0], ds_obj["category_id"][1], product, match_dicts
            )

            # Etape 2 : Vérifier si l'unité de mesure existe
            uoms = obj_obj.search(
                [
                    ("factor", "=", ds_obj["factor"]),
                    ("uom_type", "=", ds_obj["uom_type"]),
                    ("category_id", "=", categ.id),
                ]
            )

            if uoms:
                if len(uoms) > 1:
                    # Ajout d'un filtre sur le nom pour préciser la recherche
                    uoms = obj_obj.search([("id", "in", uoms.ids), ("name", "=ilike", res_name)]) or uoms
                if len(uoms) > 1:
                    # Tentative de matching par xml_id
                    uoms = uoms & datastore_matching_model(obj, res_id) or uoms
                if len(uoms) > 1:
                    # Ajout d'un filtre sur le nom pour préciser la recherche : même préfixe sur 4 lettres
                    uoms = obj_obj.search([("id", "in", uoms.ids), ("name", "=ilike", f"{res_name[:4]}%")]) or uoms
                if len(uoms) > 1:
                    # Ajout d'un filtre sur la précision de l'arrondi pour préciser la recherche
                    uoms = obj_obj.search([("id", "in", uoms.ids), ("rounding", "=", ds_obj["rounding"])]) or uoms
                result = uoms[0]
            elif create:
                # Etape 3 : Créer l'unité de mesure
                uom_data = {
                    "name": res_name,
                    "uom_type": ds_obj["uom_type"],
                    "factor": ds_obj["factor"],
                    "category_id": categ.id,
                    "rounding": ds_obj["rounding"],
                }
                result = obj_obj.sudo().create(uom_data)
        else:
            if obj_obj._rec_name:
                result = obj_obj.search([(obj_obj._rec_name, "=", res_name)])
                if len(result) != 1:
                    result = False
        match_dict[res_id] = result
        return result

    def _datastore_update_product_vals(self, product_vals):
        """Imports centralized items used in product_vals.

        Args:
            product_vals (list): List of x2many rules.

        Returns:
            list: product_vals updated with item ids after import.
        """
        vals = []
        new_products = self.env["product.template"]
        for val in product_vals:
            if val[0] == Command.SET:
                pass
            elif val[1] < 0:
                product = self.env["product.template"].browse(val[1]).of_ds_import()
                val = list(val)
                val[1] = product.id
                new_products |= product
            vals.append(val)
        return vals, new_products

    def _ds_handle_brands_categories(self):
        """
        Handle the synchronization of brands and categories with the datastore.
        """
        self = self.with_context(of_datastore_update_categ=False, no_clear_datastore_cache=True)
        categ_ids = {name: categ_id for categ_id, name in self.env["product.category"].search([]).name_get()}
        categ_obj = self.env["of.import.product.categ.config"]
        with contextlib.suppress(Exception):
            categ_obj.check_access_rights("create")
            categ_obj.check_access_rights("write")

            supplier_clients = {}
            # Récupération dans supplier_categs des correspondances deja renseignées

            for brand in self:
                supplier = brand.datastore_supplier_id
                if not supplier:
                    brand.categ_ids.filtered("is_datastore_matched").write({"is_datastore_matched": False})
                    continue

                if supplier not in supplier_clients:
                    supplier_clients[supplier] = supplier.of_datastore_connect()
                client = supplier_clients[supplier]

                if isinstance(client, str):
                    # Echec de la connexion à la base fournisseur
                    brand.categ_ids.filtered("is_datastore_matched").write({"is_datastore_matched": False})
                    brand.datastore_note_update = f"Error\n{client}"
                    continue

                stored_categs = {categ.categ_origin: categ for categ in brand.categ_ids}

                # Récupération des catégories de produits de la base du fournisseur
                # On ne prend que les catégories contenant au moins 1 article de la marque
                ds_product_obj = supplier.of_datastore_get_model(client, "product.template")
                ds_products_vals = supplier.with_context(active_test=False).of_datastore_read_group(
                    ds_product_obj,
                    [("brand_id", "=", brand.datastore_brand_id)],
                    ["categ_id"],
                    "categ_id",
                    offset=None,
                    limit=None,
                    orderby=None,
                    lazy=None,
                )

                categs = categ_obj.browse()
                for ds_product in ds_products_vals:
                    categ_origin = ds_product["categ_id"][1]
                    if stored_categ := stored_categs.pop(categ_origin, False):
                        if not stored_categ.is_datastore_matched:
                            stored_categ.is_datastore_matched = True
                        categs += stored_categ
                    else:
                        categs += categ_obj.create(
                            {
                                "brand_id": brand.id,
                                "of_import_categ_id": categ_ids.get(categ_origin, False),
                                "categ_origin": categ_origin,
                                "is_datastore_matched": True,
                            }
                        )
                for categ in iter(stored_categs.values()):
                    if (
                        categ.of_import_sale_price
                        or categ.of_import_discount
                        or categ.of_import_cost_price
                        or categ.of_import_categ_id
                    ):
                        # Une configuration a été saisie, on la garde par sentimentalité
                        if categ.is_datastore_matched:
                            categ.is_datastore_matched = False
                        categs += categ
                    else:
                        categ.unlink()

                brand.categ_ids = categs
