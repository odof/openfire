# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.osv.expression import FALSE_LEAF, NEGATIVE_TERM_OPERATORS, TERM_OPERATORS_NEGATION, TRUE_LEAF, is_leaf

from odoo.addons.of_datastore.models.of_datastore_model import DATASTORE_IND


class OFProductMixin(models.AbstractModel):
    _name = "of.product.mixin"

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        brands, args = self.of_datastore_update_domain(args)

        # Recherche sur la base du fournisseur
        if brands:
            supplier = brands[0].datastore_supplier_id

            res = self.of_ds_search(supplier, args, offset, limit, order, count)

            if not count:
                supplier_value = supplier.id * DATASTORE_IND
                res = [-(product_id + supplier_value) for product_id in res]

            return res

        if not brands:  # Éxecution de la requête sur la base courante
            return super()._search(
                args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid
            )

    @api.model
    def of_ds_import_uom(self, base, value):
        if not value:
            return False

        if value[0] > 0:
            return value[0]

        base_uom_id = (-value[0]) % DATASTORE_IND

        # on cherche d'abord dans les uom existantes :
        if uom := self.env["uom.uom"].search(
            ["|", ("of_datastore_res_id", "=", base_uom_id), ("of_datastore_res_id", "like", f"#{base_uom_id}#")],
            limit=1,
        ):
            return uom.id

        # on doit chercher localement si on a une unité compatible avec celle là
        # pour ça, on doit chercher d'autres informations sur l'uom et sa catégorie
        base_uom = self.env["uom.uom"].of_ds_read(base, [base_uom_id], self.env["uom.uom"].of_ds_fields_to_fetch())
        # on va chercher localement si on a bien un uom avec les mêmes infos
        if len(base_uom) > 0:
            base_uom = base_uom[0]
            base_categ_uom_id = (-base_uom["category_id"][0]) % DATASTORE_IND

            # on doit chercher si la catégorie est la même également
            base_categ_uom = self.env["uom.category"].of_ds_read(
                base, [base_categ_uom_id], self.env["uom.category"].of_ds_fields_to_fetch()
            )
            if len(base_categ_uom) > 0:
                base_categ_uom = base_categ_uom[0]
                uom_categ = self.env["uom.category"].search([("name", "=", base_categ_uom["name"])])
                if not uom_categ:
                    # on doit la créer du coup
                    uom_categ = self.env["uom.category"].create({"name": base_categ_uom["name"]})

                uom = self.env["uom.uom"].search(
                    [
                        ("name", "=", base_uom["name"]),
                        ("uom_type", "=", base_uom["uom_type"]),
                        ("factor", "=", base_uom["factor"]),
                        ("category_id", "=", uom_categ.id),
                    ]
                )
                if uom:
                    if uom.of_datastore_res_ids:
                        uom.of_datastore_res_ids += f"#{base_uom_id}#"
                    else:
                        uom.of_datastore_res_ids = f"#{base_uom_id}#"

                if not uom:
                    if base_uom["uom_type"] == "reference":
                        # on ne doit avoir qu'un uom de type référence dans une catégorie
                        # si on en a déjà une, on prend celle ci au lieu d'en créér une
                        uom = self.env["uom.uom"].search(
                            [("category_id", "=", uom_categ.id), ("uom_type", "=", "reference")], limit=1
                        )
                        if uom:
                            return uom.id
                    # on crée l'uom localement
                    uom = self.env["uom.uom"].create(
                        {
                            "name": base_uom["name"],
                            "uom_type": base_uom["uom_type"],
                            "factor": base_uom["factor"],
                            "category_id": uom_categ.id,
                            "of_datastore_res_id": base_uom_id,
                            "of_datastore_res_ids": f"#{base_uom_id}#",
                        }
                    )
                return uom.id

        return False

    def compute_product_price(self, brand, values):
        # TODO : version plus complète avec les formules
        # On a mis brand dans les paramètres car on va l'utiliser quand on modifiera la fct
        if of_seller_pp_untaxed := values.get("of_seller_pp_untaxed"):
            values["list_price"] = of_seller_pp_untaxed

        if of_seller_price := values.get("of_seller_price"):
            values["standard_price"] = of_seller_price
        return values

    @api.model
    def of_datastore_update_domain(self, domain):
        """
        Checks if the domain indicates a search on a supplier database.
        If yes, returns the appropriate search domain for the supplier database.

        Returns:
            tuple: (Supplier Id (of.datastore.supplier) or False otherwise, followed by the new search domain)
        """
        if "is_of_ds_search" not in str(domain):
            return False, domain
        res_domain = []
        for element in domain:
            if is_leaf(element):
                if element[0] == "is_of_ds_search":
                    element = [1, "=", 1]
            res_domain.append(element)
            # --> ici on modifie le brand_id car on cherche dans le distant
        domain = res_domain

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
        res_domain = []
        for leaf in domain:
            if is_leaf(leaf):
                if type(leaf[0]) is str and leaf[0].startswith("ds_"):
                    leaf = [leaf[0][3:], leaf[1], leaf[2]]
                elif leaf[0] in ("categ_id", "brand_id"):
                    obj_name = self._fields[leaf[0]].comodel_name
                    if new_arg := parse_domain(leaf, self.env[obj_name]):
                        leaf = new_arg
            res_domain.append(leaf)
        return brands, res_domain

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
            # Une catégorie d'articles peut avoir une correspondance différente selon la marque ou l'article.
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
