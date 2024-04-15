# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import copy

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import FALSE_LEAF, NEGATIVE_TERM_OPERATORS, TERM_OPERATORS_NEGATION, TRUE_LEAF
from odoo.tools.safe_eval import safe_eval

from .product_supplierinfo import _of_datastore_is_computed_field

# 100.000.000 ids devraient suffire pour les produits. Les chiffres suivants serviront pour le fournisseur
DATASTORE_IND = 100000000


class OFDatastoreCentralized(models.AbstractModel):
    _name = "of.datastore.centralized"
    _description = "OF Centralized Datastore"

    of_datastore_res_id = fields.Integer(string="ID on supplier database", index=True, copy=False)

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def read(self, fields=None, load="_classic_read"):
        positive_ids = [i for i in self._ids if i > 0]
        res = super(OFDatastoreCentralized, self.browse(positive_ids)).read(fields, load=load)

        if len(positive_ids) != len(self._ids):
            res = self._ds_read_process(res, fields, load)
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        brands, domain = self.of_datastore_update_domain(domain)
        if not brands:  # Éxecution de la requête sur la base courante
            return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

        # Recherche sur la base du fournisseur
        return self._of_datastore_read_group(brands, domain, fields, groupby, offset, limit, orderby, lazy)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        brands, args = self.of_datastore_update_domain(args)

        if not brands:  # Éxecution de la requête sur la base courante
            return super()._search(
                args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid
            )

        # Recherche sur la base du fournisseur
        return self._of_datastore_search(brands, args, offset, limit, order, count)

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @api.model
    def _get_datastore_unused_fields(self):
        """
        Returns the list of fields that we do not want to retrieve from the supplier (e.g. quantities in stock).
        """
        cr = self._cr

        # On ne veut aucun des champs ajoutés par les modules stock, mrp, purchase
        cr.execute(
            "SELECT f.name "
            "FROM ir_model_data AS d "
            "INNER JOIN ir_model_fields AS f "
            "  ON d.res_id=f.id "
            "WHERE d.model = 'ir.model.fields' "
            "  AND f.model = %s "
            "  AND d.module IN ('mrp','procurement','stock')",
            (self._name,),
        )
        res = [row[0] for row in cr.fetchall()]

        # Ajout de certains champs
        res += [
            "invoice_policy",
            "purchase_method",
            # Champs à valeur forcée manuellement pour l'import
            "of_import_categ_id",
            "of_import_cost_price",
            "of_import_sale_price",
            "of_import_discount",
            # Champs de notes
            "description_sale",  # Description pour les devis
            "description_purchase",  # Description pour les fournisseurs
            "description_picking",  # Description pour le ramassage
            # Champs de structure de prix
            "of_purchase_transport",
            "of_sale_transport",
            "of_sale_coeff",
            "of_other_logistic_costs",
            "of_misc_taxes",
            "of_misc_costs",
            # Champs de localisation d'inventaire
            "property_stock_production",
            "property_stock_inventory",
        ]

        # On ne veut pas non-plus les champs one2many ou many2many
        # (seller_ids, packaging_ids, champs liés aux variantes....)
        # On conserve les lignes de kits
        for field_name, field in self._fields.items():
            if field.type in ("one2many", "many2many") and (field_name != "pack_line_ids" and field_name not in res):
                res.append(field_name)
        return res

    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        """Specify if a field is a computed field in the context of the centralized database."""
        if field_name == "of_seller_name":  # Le fournisseur est directement défini par la marque
            return True
        if field_name == "of_theoretical_cost":  # Cas particulier pour le coût théorique qu'on veut récupérer du TC
            return False
        return _of_datastore_is_computed_field(self, field_name)  # from product_supplierinfo

    @api.model
    def _of_get_datastore_computed_fields(self):
        """
        Returns the list of fields that we do not want to retrieve from the supplier
        but which will have to be calculated locally (e.g. the price field which depends on the price list of
        the context).
        """
        return [field for field in self._fields if self._of_datastore_is_computed_field(field)]

    def _prepare_fields_to_read(self, fields_to_read, unused_fields, create_mode=False):
        if not create_mode:
            # Pour la lecture classique, on veut stocker tous les champs en cache pour éviter de futurs accès distants
            for field in fields_to_read:
                if field not in unused_fields:
                    fields_to_read += [field for field in self._fields if field not in fields_to_read]
                    break

        if "id" in fields_to_read:  # Le champ id sera de toute façon ajouté, le laisser générera des erreurs
            fields_to_read.remove("id")

        return fields_to_read

    def _of_ds_handle_many2one(
        self, field_res_ids, datastore_product_data, m2o_fields, create_mode, match_dicts, client, product
    ):
        """
        Handles the conversion of Many2One fields.

        Args:
            field_res_ids (dict): A dictionary to store the IDs of the retrieved records for each Many2One field.
            datastore_product_data (list): List of dictionaries representing product data from the supplier database.
            m2o_fields (list): List of Many2One fields to be handled.
            create_mode (bool): Flag indicating whether the operation is in create mode.
            match_dicts (dict): A dictionary containing mappings between fields in the supplier database and the
                central database.
            client: The client object used for communication with the supplier database.
            product: The product object for which the Many2One fields are being handled.

        Returns:
            None
        """
        obj_dict = {}
        for field in m2o_fields:
            if field in datastore_product_data[0]:
                for vals in datastore_product_data:
                    # If the field value exists and is not None
                    if vals[field]:
                        # Extract the comodel name
                        obj = self._fields[field].comodel_name
                        brand = match_dicts["brand_id"][vals["brand_id"][0]]

                        # Retrieve the corresponding record from the supplier database
                        res = brand.datastore_match(
                            client, obj, vals[field][0], vals[field][1], product, match_dicts, create=create_mode
                        )
                        if field in ("categ_id", "uom_id", "uom_po_id"):
                            obj_dict[field] = res  # Update the field value with the retrieved record ID
                        if res:
                            if res.id < 0:
                                # Valeur de la base centrale
                                # Normalement uniquement utilisé pour product_tmpl_id
                                vals[field] = (res.id, vals[field][1])
                            else:
                                vals[field] = res.id
                                field_res_ids[field].add(res.id)
                        else:
                            vals[field] = False

    def _of_ds_handle_x2many(self, o2m_fields, datastore_product_data, datastore_fields, supplier_value, create_mode):
        """The method appears to handle one-to-many fields, converting IDs to datastore format
        and preparing lines accordingly, depending on whether it's in create mode or not."""
        for field in o2m_fields:
            if field in datastore_product_data[0]:
                for vals in datastore_product_data:
                    if field not in datastore_fields:
                        continue
                    if not vals[field]:
                        continue
                    line_ids = [-(line_id + supplier_value) for line_id in vals[field]]
                    if create_mode:
                        # Preparation des lignes
                        obj = self._fields[field].comodel_name
                        obj_obj = self.env[obj]
                        vals[field] = [(5,)] + [
                            (Command.create(line.copy_data()[0])) for line in obj_obj.browse(line_ids)
                        ]
                    else:
                        # Conversion en id datastore
                        # Parcours avec indice pour ne pas recréer la liste
                        vals[field] = line_ids

    def _of_ds_handle_margin_and_discount(self, vals, obj_dict, fields_to_read, brand, product, categ_name):
        """
        Handle margin and discount calculations for the given values.
        Margin and discount calculation Margin and discount are fields calculated on the basis of sales price and
        purchase price:

        When we read the item values in the CT, we recalculate these sales and purchase prices according to the rules
        defined in the brand.

        As a result, the margin and discount must also be recalculated according to these new values.

        Args:
            vals (dict): The dictionary containing the values to be updated.
            obj_dict (dict): The dictionary containing the object's values.
            fields_to_read (list): The list of fields to be read.
            brand (object): The brand object.
            product (object): The product object.
            categ_name (str): The category name.

        Returns:
            None
        """
        # Sale/purchase price calculation
        vals.update(
            brand.compute_product_price(
                vals["of_seller_pp_ht"],
                categ_name,
                obj_dict["uom_id"],
                obj_dict["uom_po_id"],
                product=product,
                price=vals["of_seller_price"],
                remise=None,
                # remove standard_price from vals because in some cases we don't want to update it
                cost=vals.pop("standard_price", None),
                based_on_price=vals["of_is_net_price"],
            )
        )
        # Margin and discount calculation
        if "of_seller_remise" in fields_to_read:
            vals["of_seller_remise"] = (
                vals["of_seller_pp_ht"]
                and (vals["of_seller_pp_ht"] - vals["of_seller_price"]) * 100 / vals["of_seller_pp_ht"]
            )
        if "marge" in fields_to_read:
            vals["marge"] = (
                vals["list_price"] and (vals["list_price"] - vals.get("standard_price", 0)) * 100 / vals["list_price"]
            )

    def _of_read_datastore(self, fields_to_read, create_mode=False):
        """
        Reads product data from their supplier database.

        Args:
            fields_to_read (list): The list of fields to be read.
            create_mode (bool): Flag indicating whether the operation is in create mode.

        Returns:
            list: The list of dictionaries containing the product data.

        Notes:

            Some fields are necessary for the calculation of other fields:
                * brand_id: the brand, from which the reading rules are extracted
                * categ_id: the category, which may correspond to more specific reading rules within the brand
                * product_tmpl_id: Basic item, useful for of_tmpl_datastore_res_id
                * default_code: Item reference, useful for of_seller_product_code
                * uom_id and uom_po_id: The item's units of measurement and purchase measurement, useful for calculating
                purchase/sale prices
                * list_price: The purchase price of the item, from which sales price and cost calculations are made

            In create mode (create_mode == True), these fields are mandatory and therefore already present in
            `fields_to_read`.

            In classic read mode (create_mode == False), we test whether at least one field in fields_to_read
            requires remote access (with self._get_datastore_unused_fields()).

            If so, we load fields_to_read with all the fields of the current object in order to populate our cache
            and avoid multiplying remote accesses.
        """
        unused_fields = self._get_datastore_unused_fields() + self._of_get_datastore_computed_fields()

        supplier_obj = self.env["of.datastore.supplier"]
        product_tmpl_obj = self.env["product.template"]
        result = []
        fields_to_read = self._prepare_fields_to_read(fields_to_read, unused_fields, create_mode=False)
        # Articles par fournisseur
        datastore_product_ids = {}

        # Produits par fournisseur
        for full_id in self._ids:
            supplier_id = -full_id / DATASTORE_IND
            datastore_product_ids.setdefault(supplier_id, []).append((-full_id) % DATASTORE_IND)

        # Champs a valeurs spécifiques
        fields_defaults = [
            ("of_datastore_supplier_id", lambda: create_mode and supplier_id or supplier.sudo().name_get()[0]),
            ("of_datastore_res_id", lambda: vals["id"]),
            ("of_seller_pp_ht", lambda: vals["of_seller_pp_ht"]),
            ("of_seller_product_category_name", lambda: vals["categ_id"][1]),
            ("of_tmpl_datastore_res_id", lambda: vals["product_tmpl_id"][0]),
            ("description_norme", lambda: product.description_norme or vals["description_norme"]),
            ("of_template_image", lambda: vals.get("of_template_image") or product.image),
            # Attention, l'ordre des deux lignes suivantes est important
            ("of_seller_product_code", lambda: vals["default_code"]),
            ("default_code", lambda: default_code_func[brand](vals["default_code"])),
        ]

        fields_defaults = [(k, v) for k, v in fields_defaults if k in fields_to_read]
        if create_mode:
            # Ajout des champs nécessaires à la creation du product_supplierinfo
            for field in ("of_seller_delay",):
                if field not in fields_to_read:
                    fields_to_read.append(field)

            # Création de la relation fournisseur
            fields_defaults.append(
                (
                    "seller_ids",
                    lambda: [
                        Command.clear(),
                        Command.create(
                            {
                                "name": brand.partner_id.id,
                                "min_qty": 1,
                                "delay": vals["of_seller_delay"],
                            }
                        ),
                    ],
                )
            )

        datastore_fields = [field for field in fields_to_read if field not in unused_fields]

        m2o_fields = [
            field
            for field in datastore_fields
            if self._fields[field].type == "many2one" and field != "of_datastore_supplier_id"
        ]

        o2m_fields = ["pack_line_ids"]

        for supplier_id, product_ids in iter(datastore_product_ids.items()):
            supplier_value = supplier_id * DATASTORE_IND
            if not datastore_fields:
                if create_mode:
                    result += [{"id": product_id} for product_id in product_ids]
                else:
                    # Pas d'accès à la base centrale, on remplit l'id et on met tout le reste à False ou []
                    datastore_defaults = {
                        field: [] if self._fields[field].type in ("one2many", "many2many") else False
                        for field in fields_to_read
                        if field != "id"
                    }
                    result += [
                        dict(datastore_defaults, id=-(product_id + supplier_value)) for product_id in product_ids
                    ]
                continue
            supplier = supplier_obj.browse(supplier_id)
            client = supplier.of_datastore_connect()
            ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)

            datastore_product_data = supplier_obj.of_datastore_read(
                ds_product_obj, product_ids, datastore_fields, "_classic_read"
            )

            if not create_mode:
                # Les champs manquants dans la table du fournisseur ne sont pas renvoyés, sans générer d'erreur
                # Il faut donc leur attribuer une valeur par défaut
                missing_fields = [field for field in fields_to_read if field not in datastore_product_data[0]]
                # Valeur remplie en 2 étapes
                # 1 : on met une valeur vide (False ou [] pour des one2many)
                datastore_defaults = {
                    field: [] if self._fields[field].type in ("one2many", "many2many") else False
                    for field in missing_fields
                }
                # 2 : On renseigne les valeurs qui sont trouvées avec la fonction default_get
                datastore_defaults.update(product_tmpl_obj.default_get(missing_fields))

            # Traitement des données
            match_dicts = {"brand_id": {brand.datastore_brand_id: brand for brand in supplier.brand_ids}}

            # Calcul de la fonction à appliquer sur la référence des articles de chaque marque
            if "default_code" in fields_to_read:
                default_code_func = supplier.get_product_code_convert_func(client)

            datastore_read_m2o_fields = [field for field in m2o_fields if field in datastore_product_data[0]]
            field_res_ids = {field: set() for field in datastore_read_m2o_fields}
            for vals in datastore_product_data:
                # --- Calculs préalables ---
                brand = match_dicts["brand_id"][vals["brand_id"][0]]
                # Ajouter un search par article est coûteux.
                # Tant pis pour les règles d'accès, on fait une recherche SQL
                if self._name == "product.template":
                    self._cr.execute(
                        "SELECT id FROM product_template " "WHERE brand_id = %s AND of_datastore_res_id = %s",
                        (brand.id, vals["id"]),
                    )
                else:
                    self._cr.execute(
                        "SELECT t.id FROM product_product p "
                        "INNER JOIN product_template t ON t.id=p.product_tmpl_id "
                        "WHERE t.brand_id = %s AND p.of_datastore_res_id = %s",
                        (brand.id, vals["id"]),
                    )
                rows = self._cr.fetchall()
                product = product_tmpl_obj.browse(rows and rows[0][0])
                categ_name = vals["categ_id"][1]
                obj_dict = {}

                # Calcul des valeurs spécifiques
                for field, val in fields_defaults:
                    vals[field] = val()
                if create_mode:
                    del vals["id"]
                else:
                    vals["id"] = -(vals["id"] + supplier_value)
                    vals.update(datastore_defaults)

                # ---- Champs many2one ---
                self._of_ds_handle_many2one(
                    field_res_ids, datastore_product_data, m2o_fields, create_mode, match_dicts, client, product
                )

                # --- Champs x2many ---
                self._of_ds_handle_x2many(
                    o2m_fields, datastore_product_data, datastore_fields, supplier_value, create_mode
                )

                # --- Champs spéciaux ---
                vals["of_datastore_has_link"] = bool(product)

                self._of_ds_handle_margin_and_discount(
                    vals, match_dicts, obj_dict, fields_to_read, brand, product, categ_name
                )

            if not create_mode:
                # Conversion au format many2one (id,name)
                for field, res_ids in iter(field_res_ids.items()):
                    if not res_ids:
                        continue

                    obj = self._fields[field].comodel_name
                    res_obj = self.env[obj].browse(res_ids)
                    res_names = {v[0]: v for v in res_obj.sudo().name_get()}
                    for vals in datastore_product_data:
                        # Test en deux temps car en python, False est une instance de int
                        if vals.get(field) and isinstance(vals[field], int):
                            vals[field] = res_names[vals[field]]

            result += datastore_product_data
        return result

    @api.model
    def of_datastore_update_domain(self, domain):
        """
        Checks if the domain indicates a search on a supplier database.
        If yes, returns the appropriate search domain for the supplier database.

        If args contains a tuple whose first argument is 'ds_supplier_search_id',
        the second argument must be '='

        Returns:
            tuple: (Supplier Id (of.datastore.supplier) or False otherwise, followed by the new search domain)
        """
        if "of_datastore_product_search" not in domain:
            return False, domain

        domain = [copy.copy(arg) for arg in domain if arg != "of_datastore_product_search"]

        # Recherche des marques
        brand_domain = []
        for arg in domain:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0] == "brand_id":
                operator, right = arg[1], arg[2]
                # resolve string-based m2o criterion into IDs
                if (
                    isinstance(right, str)
                    or right
                    and isinstance(right, (tuple, list))
                    and all(isinstance(item, str) for item in right)
                ):
                    brand_domain.append(("name", operator, right))
                else:
                    brand_domain.append(("id", operator, right))
        brands = self.env["of.product.brand"].search(brand_domain)
        ds_supplier = brands.mapped("datastore_supplier_id")

        if not ds_supplier:
            if brands:
                raise UserError(_("Selected brands are not centralized : %s") % ", ".join(brands.mapped("name")))
            return False, [FALSE_LEAF]

        if len(ds_supplier) > 1:
            raise UserError(
                _(
                    "You must select one or several brands using the same centralized database "
                    "(provided by the same supplier)."
                )
            )
        brands = brands.filtered("datastore_supplier_id")

        # Recherche des produits non déjà enregistrés
        if self._context.get("datastore_not_stored"):
            orig_ids = (
                self.sudo()
                .with_context(active_test=False)
                .search([("brand_id", "in", brands._ids), ("of_datastore_res_id", "!=", False)])
                .mapped("of_datastore_res_id")
            )
            domain.append(("id", "not in", orig_ids))

        parse_domain = self._of_datastore_update_domain_item

        # Conversion des champs
        for arg in domain:
            if not isinstance(arg, (list, tuple)):
                continue
            if arg[0].startswith("ds_"):
                arg[0] = arg[0][3:]
            elif arg[0] in ("categ_id", "brand_id"):
                obj_name = self._fields[arg[0]].comodel_name
                if new_arg := parse_domain(arg, self.env[obj_name]):
                    arg[0], arg[1], arg[2] = new_arg
        return brands, domain

    @api.model
    def _of_datastore_update_domain_item(self, domain, obj):
        """Convert a domain element for use on the central base

        Args:
            domain (tuple): The domain element to convert
            obj (Recordset): The recordset of the object on which the domain must apply

        Returns:
            tuple: The converted domain element
        """
        left, operator, right = domain
        if obj._name == "product.category":
            # Une categorie d'articles peut avoir une correspondance différente selon la marque ou l'article.
            # La conversion est compliquée
            if (
                isinstance(right, str)
                or right
                and isinstance(right, (tuple, list))
                and all(isinstance(item, str) for item in right)
            ):
                return False
            elif isinstance(right, int) and right < 0:
                return domain
            else:
                return TRUE_LEAF

        if operator in NEGATIVE_TERM_OPERATORS:
            operator = TERM_OPERATORS_NEGATION[operator]
            new_operator = "not in"
        else:
            new_operator = "in"

        if (
            isinstance(right, str)
            or right
            and isinstance(right, (tuple, list))
            and all(isinstance(item, str) for item in right)
        ):
            obj_domain = [("name", operator, right)]
        else:
            obj_domain = [("id", operator, right)]
        obj = obj.search(obj_domain)

        result = False
        if obj._name == "of.product.brand":
            result = (left, new_operator, obj.mapped("datastore_brand_id"))
        return result

    def _of_datastore_read_group(self, brands, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
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

    def _of_datastore_search(self, brands, args, offset=0, limit=None, order=None, count=False):
        """
        Perform a search operation on the centralized datastore.

        Args:
            brands (RecordSet): The brands for which the search operation is performed.
            args (list): The search criteria.
            offset (int, optional): The offset of the search results. Defaults to 0.
            limit (int, optional): The maximum number of search results to return. Defaults to None.
            order (str, optional): The order in which the search results should be sorted. Defaults to None.
            count (bool, optional): Whether to return the count of search results instead of the actual results.
                Defaults to False.

        Returns:
            list: The search results.

        Raises:
            UserError: If there is an error accessing the supplier's database.
        """
        supplier = brands[0].datastore_supplier_id
        # Ex: si la base n'a qu'une base centralisée, elle peut appeler les articles de la base distante
        #     sans autre filtre de recherche.
        # Dans ce cas, on ne veut pas les autres marques du fournisseur
        args = ["&", ("brand_id", "in", brands.mapped("datastore_brand_id"))] + args

        supplier_obj = self.env["of.datastore.supplier"]

        # Exécution de la requête sur la base du fournisseur
        client = supplier.of_datastore_connect()
        if isinstance(client, str):  # Échec de la connexion à la base fournisseur
            raise UserError(_("Access error : %(dbname)s", supplier.db_name))

        ds_product_obj = supplier_obj.of_datastore_get_model(client, self._name)
        res = supplier_obj.of_datastore_search(ds_product_obj, args, offset, limit, order, count)

        if not count:
            supplier_value = supplier.id * DATASTORE_IND
            res = [-(product_id + supplier_value) for product_id in res]
        return res

    @api.model
    def _of_datastore_name_search(self, res, brands, name, args, operator, limit):
        """
        Perform a name search in the centralized datastore.

        Args:
            res (list): The initial search result.
            brands (recordset): The brands to search in the centralized datastore.
            name (str): The name to search for.
            args (list): Additional search criteria.
            operator (str): The search operator.
            limit (int): The maximum number of results to return.

        Returns:
            list: The updated search result after performing the name search in the centralized datastore.
        """
        supplier = brands.mapped("datastore_supplier_id")
        if len(supplier) != 1:
            # Les marques doivent être centralisées, une seule base centrale à la fois
            return res

        if limit != 8 or len(res) == limit:
            # La recherche sur une base fournisseur ne se fait en automatique que pour les recherches
            #   dynamiques des champs many2one (limit=8)
            return res
        if len(res) == 7:
            # Le 8e produit ne sert qu'à savoir si on affiche "Plus de résultats"
            return res + [(False, "")]

        # Recherche des produits dans la base centrale
        client = supplier.of_datastore_connect()
        if isinstance(client, str):
            # Échec de la connexion à la base fournisseur
            return res

        brands = brands.filtered("datastore_supplier_id")

        # Recherche des produits non déjà enregistrés
        orig_ids = (
            self.with_context(active_test=False)
            .search([("brand_id", "in", brands._ids), ("of_datastore_res_id", "!=", False)])
            .mapped("of_datastore_res_id")
        )

        # Mise a jour des paramètres de recherche
        new_args = [("brand_id", "in", brands.mapped("datastore_brand_id")), ("id", "not in", orig_ids)] + list(
            args or []
        )

        ds_product_obj = supplier.of_datastore_get_model(client, self._name)
        res2 = supplier.of_datastore_name_search(ds_product_obj, name, new_args, operator, limit - len(res))
        supplier_ind = DATASTORE_IND * supplier["id"]

        default_code_func = supplier.get_product_code_convert_func(client)
        if len(brands) == 1:
            func = default_code_func[brands]
            res += [
                [-(pid + supplier_ind), f"[{func(pname[1:])}]" if pname.startswith("[") else pname]
                for pid, pname in res2
            ]
        else:
            brand_match = {brand.datastore_brand_id: brand for brand in supplier.brand_ids}
            ds_products_brand = supplier.of_datastore_read(ds_product_obj, zip(*res2)[0], ["brand_id"])
            ds_products_brand = {  # {clef=identifiant article sur base centrale : valeur=marque sur base courante}
                data["id"]: brand_match[data["brand_id"][0]] for data in ds_products_brand
            }
            res += [
                [
                    -(pid + supplier_ind),
                    f"[{default_code_func[ds_products_brand[pid]](pname[1:])}]" if pname.startswith("[") else pname,
                ]
                for pid, pname in res2
            ]
        return res

    def _ds_read_process(self, res, fields, load):
        """
        Process the read operation for the given ids in the centralized datastore.

        Args:
            res (dict): The result dictionary containing the data for the given ids.
            fields (list): The list of fields to be read.
            load (str): The load mode for the read operation.

        Returns:
            list: The processed results in the correct order.
        """
        cache_obj = self.env["of.datastore.cache"]

        self.check_access_rights("read")
        fields = self.check_field_access_rights("read", fields)
        fields = set(fields)

        if "id" in fields:
            fields.remove("id")

        obj_fields = [self._fields[field] for field in fields]
        use_name_get = load == "_classic_read"

        # Gestion à part des modèles d'articles, sans quoi of_read_datastore sera appelé pour name_get()
        #   une fois par modèle.
        read_tmpl = self._fields.get("product_tmpl_id") in obj_fields
        tmpl_values = {}

        # Séparation des ids par base centrale
        datastore_product_ids = {}
        for full_id in self._ids:
            if full_id < 0:
                datastore_product_ids.setdefault(-full_id / DATASTORE_IND, []).append(full_id)

        res = {vals["id"]: vals for vals in res}
        for supplier_id, datastore_ids in iter(datastore_product_ids.items()):
            with self.env["of.datastore.cache"]._get_cache_token(supplier_id) as of_cache:
                # Vérification des données dans notre cache
                cached_products = of_cache.search([("model", "=", self._name), ("res_id", "in", datastore_ids)])

                # Les articles non en cache sont à lire
                new_ids = set(datastore_ids) - set(cached_products.mapped("res_id"))

                # Si au moins un objet est inexistant en cache, tous les champs sont à lire
                new_fields = set(fields) if new_ids else set()

                # Les articles dont au moins un champ n'est pas en cache sont aussi à lire, pour au moins ce champ
                for cached_product in cached_products:
                    product_data = safe_eval(cached_product.vals)
                    if missing_fields := fields - set(product_data.keys()):
                        new_fields |= missing_fields
                        new_ids.add(cached_product.res_id)
                    if read_tmpl and "product_tmpl_id" in product_data:
                        tmpl_values[product_data["product_tmpl_id"][0]] = product_data["product_tmpl_id"]

                if new_ids:
                    # Lecture des données sur la base centrale
                    data = self.browse(new_ids)._of_read_datastore(list(new_fields), create_mode=False)

                    # Stockage des données dans notre cache
                    of_cache.store_values(self._name, data)

                    if read_tmpl and "product_tmpl_id" in new_fields:
                        for d in data:
                            tmpl_values[d["product_tmpl_id"][0]] = d["product_tmpl_id"]

            for obj in self.browse(datastore_ids):
                # Il faut charger les valeurs dans le cache manuellement car elles ne se chargent de façon
                #   automatique que si le cache est vide, ce qui n'est plus le cas à ce stade.
                cache_obj.apply_values(obj)
                # Filtre des champs à récupérer et conversion au format read
                vals = {field.name: field.convert_to_read(obj[field.name], self, use_name_get) for field in obj_fields}
                vals["id"] = obj.id
                res[obj.id] = vals

                if read_tmpl:
                    vals["product_tmpl_id"] = tmpl_values[obj.product_tmpl_id.id]

        # Remise des résultats dans le bon ordre
        return [res[i] for i in self._ids]
