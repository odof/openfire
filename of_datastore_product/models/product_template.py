# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextlib import suppress

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.of_datastore.models.of_datastore_cache import DS_CACHE
from odoo.addons.of_datastore.models.of_datastore_model import DATASTORE_IND


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "of.datastore.model", "of.product.mixin"]

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

    def of_ds_match_many2one(self, value, base_index, data):
        # on retourne un id négatif basé sur l'index de la base distante
        return (-(value[0] + base_index), value[1])

    def of_ds_fields_to_fetch(self):
        res = super().of_ds_fields_to_fetch()
        res += [
            "cost_currency_id",
            "currency_id",
            "product_variant_id",
            "product_variant_count",
            "product_variant_ids",
            "attribute_line_ids",
            "is_product_variant",
            "product_tag_ids",
            "categ_id",
            "of_seller_product_category_name",
            "image_1920",
            "type",
            "of_seller_delay",
            "brand_id",
            "uom_id",
            "uom_po_id",
            "of_seller_price",
            "of_is_net_price",
            "display_name",
            "taxes_id",
            "pack_line_ids",
            "sale_line_warn_msg",
            "purchase_line_warn_msg",
        ]
        return list(set(res))

    def of_ds_fields_to_force_read(self):
        res = super().of_ds_fields_to_force_read()
        # on ajoute ces champs là car ils sont liés à la variante du produit qui n'existe pas encore
        res += ["pack_line_ids", "standard_price"]
        return list(set(res))

    def of_ds_fields_to_not_fetch(self):
        res = super().of_ds_fields_to_not_fetch()
        res += [
            "of_import_categ_id",
            "product_tag_ids",
            "dont_create_move",
            "create_uid",
            "of_display_supplier_stock_button",
            "of_datastore_res_id",
            "is_of_ds_search",
            "write_uid",
            "responsible_id",
            "message_ids",
            "message_follower_ids",
            "message_partner_ids",
            "message_main_attachment_id",
            "has_message",
            "activity_ids",
        ]
        return list(set(res))

    def of_ds_fields_to_calculate(self):
        res = super().of_ds_fields_to_calculate()
        res += [
            "of_seller_discount",
            "of_margin",
            "of_datastore_supplier_id",
            "of_datastore_res_id",
            "of_seller_product_code",
            "default_code",
            "display_name",
            "categ_id",
            "standard_price",
            "list_price",
        ]
        return list(set(res))

    def of_ds_set_calculate_values(self, list_res, base):
        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)
        # on mets à jour chaque ligne avec des valeurs par défaut
        # attention, chaque méthode super devra mettre à jour le ds_cache et le cache odoo
        list_res = super().of_ds_set_calculate_values(list_res, base)
        default_code_func = base.get_product_code_convert_func()

        for res in list_res:
            res["of_seller_product_code"] = res["default_code"]
            res["of_datastore_supplier_id"] = (base.id, base.db_name)
            res["of_datastore_res_id"] = -res["id"] % DATASTORE_IND

            brand = self.env["of.product.brand"].browse(res["brand_id"][0])

            if brand:
                brand_categ = brand.categ_ids.filtered(lambda r: r.categ_origin == res["categ_id"][0])
                if brand_categ:
                    res["categ_id"] = (brand_categ.of_import_categ_id.id, brand_categ.of_import_categ_id.name)
                else:
                    res["categ_id"] = (brand.of_import_categ_id.id, brand.of_import_categ_id.name)

                res["default_code"] = default_code_func[brand](res["default_code"])
                res["display_name"] = res["display_name"].replace(res["of_seller_product_code"], res["default_code"])

                res = self.compute_product_price(brand, res)

            if (seller_pp_untaxed := res.get("of_seller_pp_untaxed")) and (seller_price := res.get("of_seller_price")):
                res["of_seller_discount"] = (seller_pp_untaxed - seller_price) * 100 / seller_pp_untaxed

            if (list_price := res.get("list_price")) and (standard_price := res.get("standard_price", 0)):
                res["of_margin"] = (list_price - standard_price) * 100 / list_price

        # on doit mettre les nouvelles valeurs dans le cache
        fields_to_cache = [
            "of_seller_discount",
            "of_margin",
            "of_datastore_supplier_id",
            "of_datastore_res_id",
            "of_seller_product_code",
            "default_code",
            "product_template_attribute_value_ids",
            "display_name",
            "categ_id",
            "standard_price",
            "list_price",
        ]
        for line in list_res:
            record = self.browse(line["id"])
            for field_to_cache in fields_to_cache:
                if field := record._fields.get(field_to_cache, False):
                    if field_to_cache in line:
                        ds_cache.set(
                            record, field, field.convert_to_cache(line[field_to_cache], record, validate=False)
                        )
        return list_res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        brands, domain = self.of_datastore_update_domain(domain)
        if not brands:  # Éxecution de la requête sur la base courante
            return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

        # Recherche sur la base du fournisseur
        return self._of_ds_read_group(brands, domain, fields, groupby, offset, limit, orderby, lazy)

    def _of_ds_read_group(self, brands, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
        Read records from the centralized datastore and perform a group by operation.

        Args:
            brands (RecordSet): The brands for which to retrieve the records.
            domain (list): The search domain to filter the records.
            fields (list): The fields to include in the result.
            groupby (list): The fields to group the records by.
            offset (int): The number of records to skip from the beginning.
            limit (int): The maximum number of records to retrieve.
            orderby (bool): Whether to sort the records.
            lazy (bool): Whether to perform the operation lazily.

        Returns:
            list: The result of the group by operation.

        Raises:
            UserError: If there is an access error or connection failure to the supplier's database.

        """
        supplier = brands[0].datastore_supplier_id
        # Ex: si la base n'a qu'une base centralisée, elle peut appeler les articles de la base distante
        #     sans autre filtre de recherche.
        # Dans ce cas, on ne veut pas les autres marques du fournisseur
        domain = ["&", ("brand_id", "in", brands.mapped("datastore_brand_id"))] + domain

        supplier_obj = self.env["of.datastore.supplier"]

        # Exécution de la requête sur la base du fournisseur
        client = supplier.of_datastore_connect()
        if isinstance(client, str):
            # Échec de la connexion à la base fournisseur
            raise UserError(f"Access error {supplier.db_name}")

        ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)
        res = supplier_obj.of_datastore_read_group(
            ds_product_obj, domain, fields, groupby, offset, limit, orderby, lazy
        )
        for row in res:
            for arg in row["__domain"]:
                if isinstance(arg, (list, tuple)):
                    arg[0] = f"ds_{arg[0]}"
            row["__domain"] = ["of_datastore_product_search", ("brand_id", "in", brands.ids)] + row["__domain"]
        return res

    def get_single_product_variant(self):
        # en cas d'utilisation du configurateur de produit
        # on doit retourner la variante ici directement
        if self.id < 0:
            if self.product_variant_id:
                value = {
                    "product_id": self.product_variant_id.id,
                    "product_name": self.product_variant_id.display_name,
                }
            else:
                base_id = -self.id // DATASTORE_IND
                record_id = -self.id % DATASTORE_IND
                base = self.env["of.datastore.supplier"].browse(base_id)

                res = self.of_ds_read(base, [record_id], ["product_variant_id"], check_fields=True)
                if res:
                    value = {
                        "product_id": res[0]["product_variant_id"][0],
                        "product_name": res[0]["product_variant_id"][1],
                    }
                else:
                    # en principe on ne devrait jamais passer par là
                    value = {
                        "product_id": False,
                        "product_name": False,
                    }
            return value
        else:
            return super().get_single_product_variant()

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

        # on y ajoute une recherche distante si la limite n'est pas atteinte par la première
        # recherche
        if len(res) < limit:
            for arg in args or []:
                if not isinstance(arg, (list, tuple)):
                    continue
                if arg[0].startswith("ds_"):
                    arg[0] = arg[0][3:]
                elif arg[0] in ("categ_id", "brand_id"):
                    obj_name = self._fields[arg[0]].comodel_name
                    if new_arg := self._of_datastore_update_domain_item(arg, self.env[obj_name]):
                        arg = list(args)
                        arg[0], arg[1], arg[2] = new_arg

            # on va lancer ensuite des recherches sur les bases où sont les marques
            suppliers = brands.mapped("datastore_supplier_id")

            for supplier in suppliers:
                res2 = self.of_ds_name_search(supplier, name, args, operator, limit - len(res))
                res += list(res2)
        return res

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def of_ds_import(self):
        """
        Import products from the centralized datastore.

        This method is used to import products from the centralized datastore into the current database.
        It performs various checks and operations to ensure the data is imported correctly.

        Returns:
            product.template: The imported products as product.product records.

        Raises:
            None

        """

        vals = []
        products = self.env["product.template"]
        create_product = self.env.context.get("create_product")
        for product in self:
            # on regarde avant tout s'il n'existe pas un produit avec la même marque et la même référence
            # si c'est le cas, on retourne le produit déjà existant
            existing_product = self.env["product.template"].search(
                [("brand_id", "=", product.brand_id.id), ("default_code", "=", product.default_code)]
            )
            if existing_product:
                products += existing_product
                continue
            fields_to_import = product.of_ds_fields_to_import()
            # on va les chercher, soit dans le cache si les données sont dedans
            # soit dans la base distante
            base = self.env["of.datastore.supplier"].browse(-product.id // DATASTORE_IND)
            product_id = -product.id % DATASTORE_IND
            res = self.of_ds_read(base, [product_id], fields_to_import, check_fields=True)
            if res:
                product.of_ds_set_calculate_values(res, base)
                record = self.browse(product_id)
                pack_line_dict = {}
                for r in res:
                    if r.get("id", 0) < 0:
                        r["of_datastore_res_id"] = -r["id"] % DATASTORE_IND
                        r.pop("id")
                    if (
                        not create_product
                        and r.get("product_variant_id")
                        and record._fields.get("product_variant_id").convert_to_write(r["product_variant_id"], record)
                        < 0
                    ):
                        r.pop("product_variant_id")
                    for key in r:
                        field = record._fields.get(key)
                        if field:
                            if key == "product_variant_id":
                                if create_product:
                                    p_id = field.convert_to_write(r[key], record)
                                    if p_id < 0:
                                        product_product = (
                                            self.env["product.product"]
                                            .browse(p_id)
                                            .with_context({"create_product_template": False})
                                            .of_ds_import()
                                        )
                                        r[key] = product_product.id
                                    else:
                                        r[key] = p_id
                                else:
                                    r[key] = p_id
                            elif key == "pack_line_ids":
                                # on ne peut pas créée le product template directement avec les lignes de kits
                                # donc on sauvegarde et on mettra à jour à la fin les produits
                                pack_line_dict[r["default_code"]] = self.of_ds_import_pack_line_ids(base, r[key])
                                r[key] = []
                            elif key in ["uom_id", "uom_po_id"]:
                                r[key] = self.of_ds_import_uom(base, r[key])

                            else:
                                r[key] = field.convert_to_write(r[key], record)

                    if brand_id := r.get("brand_id"):
                        brand = self.env["of.product.brand"].browse(brand_id)

                        r["seller_ids"] = [
                            Command.clear(),
                            Command.create(
                                {
                                    "partner_id": brand.partner_id.id,
                                    "min_qty": 1,
                                    "delay": r.get("of_seller_delay", 0),
                                    "of_discount": r.get("of_discount", 0),
                                    "of_public_price_untaxed": r.get("of_seller_pp_untaxed"),
                                    "product_code": r.get("of_seller_product_code"),
                                    "price": r.get("list_price"),
                                }
                            ),
                        ]

                vals += res
        products += self.env["product.template"].create(vals)
        # on ajoute maintenant les lignes de kits
        for product in products:
            if product.default_code in pack_line_dict:
                product.pack_line_ids = pack_line_dict[product.default_code]
            else:
                product.pack_line_ids = []
        return products

    @api.model
    def of_ds_import_pack_line_ids(self, base, values):
        if not values:
            return []

        positive_ids = [i for i in values if i > 0]
        negative_ids = [-i % DATASTORE_IND for i in values if i < 0]

        to_creates = self.env["product.pack.line"].of_ds_read(base, negative_ids, ["product_id", "quantity"])
        res = []
        for to_create in to_creates:
            if (product_id := to_create["product_id"][0]) < 0:
                product = self.env["product.product"].browse(product_id).of_ds_import()
            else:
                product = self.env["product.product"].browse(product_id)

            # on crée la ligne
            res.append(Command.create({"product_id": product.id, "quantity": to_create["quantity"]}))

        for id in positive_ids:
            res.append(Command.link(id))

        return res
