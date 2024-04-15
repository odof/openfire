# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .of_datastore_centralized import DATASTORE_IND


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "of.datastore.centralized"]

    of_tmpl_datastore_res_id = fields.Integer(related="product_tmpl_id.of_datastore_res_id", string="PD Template's ID")
    # Champ related pour permettre l'import de l'image du modèle d'article.
    # En effet, le champ image est surchargé dans product.product pour être de type compute.
    of_template_image = fields.Binary(related="product_tmpl_id.image_1920", string="Template's image")

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        name, name_brands = self.env["product.template"].of_name_search_extract_brands(name)
        args_brands = self.env["of.product.brand"]
        for arg in args or []:
            if arg[0] == "brand_id" and arg[1] == "=" and arg[2]:
                if isinstance(arg[2], str):
                    brand = self.env["of.product.brand"].search(["|", ("name", "=", arg[2]), ("code", "=", arg[2])])
                else:
                    brand = self.env["of.product.brand"].browse(arg[2])
                args_brands += brand

        new_args = args
        if name_brands:
            new_args = [("brand_id", "in", name_brands._ids)] + list(args or [])
        res = super().name_search(name, new_args, operator, limit)

        parse_domain_func = self._of_datastore_update_domain_item
        for arg in args or []:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0].startswith("ds_"):
                arg[0] = arg[0][3:]
            elif arg[0] in ("categ_id", "brand_id"):
                obj_name = self._fields[arg[0]].comodel_name
                if new_arg := parse_domain_func(arg, self.env[obj_name]):
                    arg[0], arg[1], arg[2] = new_arg
        return self._of_datastore_name_search(res, args_brands or name_brands, name, args, operator, limit)

    def write(self, vals):
        self._ds_check_default_code_lock(vals)
        orderpoints_to_activate = self._ds_archive_replenishment_rules(vals)

        res = super().write(vals)

        # An item archived via the CT could have reapproval rules.
        # When archiving from the CT, we also set the purchase_ok field to False, allowing us to reactivate
        # the reorder rules at the same time as the article if the field is set to False.
        self._ds_activate_orderpoints(orderpoints_to_activate)
        return res

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @api.model
    def of_datastore_get_import_fields(self):
        unused_fields = self._get_datastore_unused_fields()
        computed_fields = self._of_get_datastore_computed_fields()
        import_fields = [
            f for f in self._fields if f not in computed_fields and f not in unused_fields and f != "product_tmpl_id"
        ]

        import_fields += [
            # Champs relatifs au modèle d'article
            "product_tmpl_id",
            "of_tmpl_datastore_res_id",
            # Champs relatifs au au fournisseur
            "of_seller_pp_ht",
            "of_seller_product_code",
            "of_seller_product_category_name",
            "of_seller_delay",
            # Kits
            "kit_line_ids",
        ]
        return import_fields

    @api.model
    def of_datastore_get_fields_to_not_empty(self):
        fields_name_list = [
            "barcode",
            "of_standard_id",
        ]
        fields_to_exclude = self._get_fields_to_exclude()
        fields_name_list += fields_to_exclude
        return fields_name_list

    @api.model
    def _get_fields_to_exclude(self):
        """
        Dedicated method for retrieving fields to be excluded.
        This method can be overloaded by specific modules to add or remove fields from the exclusion list.
        """
        return []

    def of_datastore_import(self):
        """
        Import products from the centralized datastore.

        This method is used to import products from the centralized datastore into the current database.
        It performs various checks and operations to ensure the data is imported correctly.

        Returns:
            product.product: The imported products as product.product records.

        Raises:
            None

        """
        self_obj = self.env[self._name]  # self_obj to avoid sending all ids in api.model calls
        if len(self) == 1:
            # Detection de l'existance du produit
            # Ce cas peut se produire dans un object de type commande, si plusieurs lignes ont la meme reference
            supplier = self.env["of.datastore.supplier"].browse(-self.id / DATASTORE_IND)

            if result := self_obj.with_context(active_test=False).search(
                [("brand_id", "in", supplier.brand_ids._ids), ("of_datastore_res_id", "=", (-self.id) % DATASTORE_IND)]
            ):
                return self_obj.browse(result._ids)

        # L'import d'articles via le tarif centralisé fait abstraction des droits de l'utilisateur.
        # En effet, les articles distants sont utilisables comme s'ils étaient déjà présents sur la base.
        self_obj = self_obj.sudo()

        fields_to_read = self.of_datastore_get_import_fields()
        products = self.browse()
        for product_data in sorted(
            self._of_read_datastore(fields_to_read, create_mode=True), key=lambda vals: vals["pack_ok"]
        ):
            # Les kits sont ajoutés en dernier pour éviter d'importer des composants après qu'ils ont été
            # importés par le kit.
            products += self_obj.create(product_data)
        return products

    def _ds_check_default_code_lock(self, vals):
        if "default_code" in vals and not self.env.context.get("of_skip_default_code_lock", False):
            for record in self:
                if record.of_datastore_res_id and vals["default_code"] != record.default_code:
                    raise ValidationError(_("You cannot change the default code of a centralized product."))

    def _ds_archive_replenishment_rules(self, vals):
        """
        Archive replenishment rules based on the provided values.

        Args:
            vals (dict): A dictionary containing the values to update.

        Returns:
            orderpoints_to_activate (bool or recordset): The orderpoints that need to be activated.
        """
        orderpoints_to_activate = False
        if "active" in vals:
            if vals["active"]:
                orderpoints_to_activate = (
                    self.filtered(lambda p: not p.active and not p.purchase_ok)
                    .with_context(active_test=False)
                    .mapped("orderpoint_ids")
                    .filtered(lambda r: not r.active)
                )
            elif self.env.context.get("of_from_product_datastore"):
                self.mapped("orderpoint_ids").filtered("active").write({"active": False})
        return orderpoints_to_activate

    def _ds_activate_orderpoints(self, orderpoints_to_activate):
        """
        Activate the given orderpoints.

        Args:
            orderpoints_to_activate (list): A list of orderpoints to activate.

        Returns:
            None
        """
        if orderpoints_to_activate:
            orderpoints_to_activate.write({"active": True})
