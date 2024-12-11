# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, api, fields, models

from odoo.addons.of_datastore.models.of_datastore_cache import DS_CACHE
from odoo.addons.of_datastore.models.of_datastore_model import DATASTORE_IND


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "of.datastore.model", "of.product.mixin"]

    of_tmpl_datastore_res_id = fields.Integer(related="product_tmpl_id.of_datastore_res_id", string="PD Template's ID")
    # Champ related pour permettre l'import de l'image du modèle d'article.
    # En effet, le champ image est surchargé dans product.product pour être de type compute.
    of_template_image = fields.Binary(related="product_tmpl_id.image_1920", string="Template's image")

    def of_ds_match_many2one(self, value, base_index, data):
        # on retourne un id négatif basé sur l'index de la base distante
        return (-(value[0] + base_index), value[1])

    def of_ds_fields_to_fetch(self):
        res = super().of_ds_fields_to_fetch()

        return res + [
            "id",
            "name",
            "display_name",
            "active",
            "default_code",
            "barcode",
            "product_tmpl_id",
            "volume",
            "weight",
            "can_image_variant_1024_be_zoomed",
            "create_uid",
            "create_date",
            "write_uid",
            "write_date",
            "of_forced_lst_price",
            "of_theoretical_cost",
            "taxes_id",
            "currency_id",
            "cost_currency_id",
            "of_seller_pp_untaxed",
            "categ_id",
            "of_seller_product_category_name",
            "image_1920",
            "type",
            "of_seller_delay",
            "brand_id",
            "pack_line_ids",
            "uom_id",
            "uom_po_id",
            "of_seller_price",
            "of_is_net_price",
            "volume",
            "sale_line_warn",
            "priority",
            "lst_price",
        ]

    def of_ds_fields_to_not_fetch(self):
        res = super().of_ds_fields_to_not_fetch()
        return res + [
            "create_uid",
            "write_uid",
            "is_of_ds_search",
            "message_main_attachment_id",
            "activity_ids",
            "message_ids",
            "message_follower_ids",
            "message_partner_ids",
            "message_main_attachment_id",
            "has_message",
        ]

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

    def of_ds_fields_to_force_read(self):
        res = super().of_ds_fields_to_force_read()
        res += ["standard_price"]
        return list(set(res))

    def of_ds_set_calculate_values(self, list_res, base):
        ds_cache = DS_CACHE.get_cache(self.env.cr.dbname)

        list_res = super().of_ds_set_calculate_values(list_res, base)
        default_code_func = base.get_product_code_convert_func()
        for res in list_res:
            res["of_datastore_supplier_id"] = (base.id, base.db_name)
            res["of_datastore_res_id"] = -res["id"] % DATASTORE_IND
            res["of_tmpl_datastore_res_id"] = -res["product_tmpl_id"][0] % DATASTORE_IND
            res["of_seller_product_code"] = res["default_code"]

            brand = self.env["of.product.brand"].browse(res["brand_id"][0])
            if brand:
                brand_categ = brand.categ_ids.filtered(lambda r: r.categ_origin == res["categ_id"][0])
                if brand_categ:
                    res["categ_id"] = (brand_categ.of_import_categ_id.id, brand_categ.of_import_categ_id.name)
                else:
                    res["categ_id"] = (brand.of_import_categ_id.id, brand.of_import_categ_id.name)

                res = self.compute_product_price(brand, res)

                res["default_code"] = default_code_func[brand](res["default_code"])
                res["display_name"] = res["display_name"].replace(res["of_seller_product_code"], res["default_code"])

            if (seller_pp_untaxed := res.get("of_seller_pp_untaxed")) and (seller_price := res.get("of_seller_price")):
                res["of_seller_discount"] = (seller_pp_untaxed - seller_price) * 100 / seller_pp_untaxed

            if (list_price := res.get("list_price")) and (standard_price := res.get("standard_price", 0)):
                res["of_margin"] = (list_price - standard_price) * 100 / list_price

            res["product_template_attribute_value_ids"] = []
        # on doit mettre les nouvelles valeurs dans le cache
        fields_to_cache = [
            "of_datastore_supplier_id",
            "of_datastore_res_id",
            "of_tmpl_datastore_res_id",
            "of_seller_product_code",
            "default_code",
            "product_tmpl_id",
            "display_name",
            "product_template_attribute_value_ids",
            "categ_id",
            "of_seller_discount",
            "of_margin",
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

    def of_ds_fields_to_import(self):
        res = self.of_ds_fields_to_fetch()
        res += ["pack_ok"]

        return res

    @api.model
    def of_ds_fields_to_not_empty(self):
        fields_name_list = [
            "barcode",
            "of_standard_id",
        ]
        return fields_name_list

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        # on va chercher si dans la recherche on a ajouté le "m:" pour chercher par marque

        name, brands = self.env["product.template"].of_name_search_extract_brands(name)
        if brands:
            args = [("brand_id", "in", brands._ids)] + list(args or [])

        # on fait d'abord une recherche locale
        res = super().name_search(name, args, operator, limit)

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
                        arg = list(arg)
                        arg[0], arg[1], arg[2] = new_arg
            # on va lancer ensuite des recherches sur les bases où sont les marques
            suppliers = brands.mapped("datastore_supplier_id")

            for supplier in suppliers:
                res2 = self.of_ds_name_search(supplier, name, args, operator, limit - len(res))
                res += list(res2)

        return res

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def of_ds_import(self):
        """
        Import products from the centralized datastore.

        This method is used to import products from the centralized datastore into the current database.
        It performs various checks and operations to ensure the data is imported correctly.

        Returns:
            product.product: The imported products as product.product records.

        Raises:
            None

        """

        vals = []
        products = self.env["product.product"]
        create_product_template = self.env.context.get("create_product_template")
        for product in self:
            existing_product = self.env["product.product"].search(
                [("brand_id", "=", product.brand_id.id), ("default_code", "=", product.default_code)]
            )
            if existing_product:
                products += existing_product
                continue
            fields_to_import = product.of_ds_fields_to_import()
            # on va les chercher, soit dans le cache si les données sont dedans
            # soit dans la base distance
            base = self.env["of.datastore.supplier"].browse(-product.id // DATASTORE_IND)
            product_id = -product.id % DATASTORE_IND
            res = self.of_ds_read(base, [product_id], fields_to_import, check_fields=True)
            if res:
                product.of_ds_set_calculate_values(res, base)
                record = self.browse(product_id)
                for r in res:
                    if r.get("id", 0) < 0:
                        r["of_datastore_res_id"] = -r["id"] % DATASTORE_IND
                        r.pop("id")
                    if (
                        not create_product_template
                        and r.get("product_tmpl_id")
                        and record._fields.get("product_tmpl_id").convert_to_write(r["product_tmpl_id"], record) < 0
                    ):
                        r.pop("product_tmpl_id")
                    for key in r:
                        field = record._fields.get(key)
                        if key == "product_tmpl_id":
                            if create_product_template:
                                p_id = field.convert_to_write(r[key], record)
                                if p_id < 0:
                                    product_tmpl = (
                                        self.env["product.template"]
                                        .browse(p_id)
                                        .with_context({"product_create": False})
                                        .of_ds_import()
                                    )
                                    r[key] = product_tmpl.id
                                else:
                                    r[key] = p_id
                            else:
                                r[key] = p_id
                        elif key == "pack_line_ids":
                            r[key] = self.of_ds_import_pack_line_ids(base, r[key])
                        elif key in ["uom_id", "uom_po_id"]:
                            r[key] = self.of_ds_import_uom(base, r[key])
                        else:
                            r[key] = field.convert_to_write(r[key], record)

                vals += res
        for product_data in sorted(vals, key=lambda r: r["pack_ok"]):
            products += self.env["product.product"].create(product_data)

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
                product = self.browse(product_id).of_ds_import()
            else:
                product = self.browse(product_id)

            # on crée la ligne
            res.append(Command.create({"product_id": product.id, "quantity": to_create["quantity"]}))

        for id in positive_ids:
            res.append(Command.link(id))

        return res
