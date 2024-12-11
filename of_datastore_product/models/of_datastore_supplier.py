# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from odoo.addons.of_datastore.models.of_datastore_model import DATASTORE_IND


class OFDatastoreSupplier(models.Model):
    _name = "of.datastore.supplier"
    _inherit = "of.datastore.connector"
    _description = "Centralized products connector"
    _rec_name = "db_name"
    _order = "db_name"

    active = fields.Boolean(default=True)
    brand_ids = fields.One2many(
        comodel_name="of.product.brand", inverse_name="datastore_supplier_id", string="Allowed brands"
    )
    datastore_brand_ids = fields.One2many(
        comodel_name="of.datastore.supplier.brand",
        compute="_compute_datastore_brand_ids",
        inverse=lambda *args: True,
        string="Supplier brands",
    )
    display_brand_ids = fields.Many2many(  # as we want a many2many_tags widget in the view we need a many2many field
        comodel_name="of.product.brand", compute="_compute_display_brand_ids", string="Allowed brands (Tags)"
    )

    _sql_constraints = [("db_name_uniq", "unique (db_name)", "There is already a connection to this database")]

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends()
    def _compute_datastore_brand_ids(self):
        supplier_brand_obj = self.env["of.datastore.supplier.brand"]
        for supplier in self:
            datastore_brands = False
            client = supplier.of_datastore_connect()
            if not isinstance(client, str):
                ds_brand_obj = self.of_datastore_get_model(client, "of.product.brand")
                if ds_brand_ids := self.of_datastore_search(ds_brand_obj, []):
                    id_add = DATASTORE_IND * supplier.id
                    ds_brand_ids = [brand_id + id_add for brand_id in ds_brand_ids]
                    datastore_brands = supplier_brand_obj.browse(ds_brand_ids)
            supplier.datastore_brand_ids = datastore_brands

    @api.depends()
    def _compute_display_brand_ids(self):
        for supplier in self:
            supplier.display_brand_ids = supplier.brand_ids

    # -------------------------------------------------------------------------
    # Onchange methods
    # -------------------------------------------------------------------------

    @api.onchange("server_address")
    def onchange_server_address(self):
        if self.server_address and not self.server_address.startswith("http"):
            return {"value": {"server_address": f"https://{self.server_address}"}}  # noqa
        return False

    @api.onchange("db_name")
    def onchange_db_name(self):
        if self.db_name:
            return {"value": {"server_address": f"https://{self.db_name}.openfire.fr"}}  # noqa
        return False

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def read(self, fields=None, load="_classic_read"):
        if fields and all(field in ("brand_ids", "db_name") for field in fields):
            # Un utilisateur non admin ne doit avoir accès qu'aux marques et db_name du connecteur TC
            # (surtout pas aux accès login/password)
            self = self.sudo()
        return super(OFDatastoreSupplier, self).read(fields, load=load)

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_dummy(self):
        return True

    def action_button_import_brands(self):
        self.ensure_one()
        wizard_obj = self.env["of.datastore.import.brand"]
        client = self.of_datastore_connect()
        if isinstance(client, str):
            raise UserError(_("Failed to connect to central base"))
        ds_brand_obj = self.of_datastore_get_model(client, "of.product.brand")
        ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
        ds_brand_data = self.of_datastore_read(ds_brand_obj, ds_brand_ids, ["name", "code", "logo", "update_note"])
        brand_names = self.env["of.product.brand"].search([]).mapped("name")

        wizard_value = {
            "datastore_supplier_id": self.id,
            "line_ids": [
                Command.create(
                    {
                        "datastore_brand_id": ds_brand["id"],
                        "name": ds_brand["name"],
                        "code": ds_brand["code"],
                        "logo": ds_brand["logo"],
                        "update_note": ds_brand["update_note"],
                        "state": "done" if ds_brand["name"] in brand_names else "do",
                    }
                )
                for ds_brand in ds_brand_data
            ],
        }
        wizard = wizard_obj.create(wizard_value)
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": wizard._name,
            "res_id": wizard.id,
            "target": "new",
        }

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def get_product_code_convert_func(self, client=False, from_datastore=True):
        """
        Get the conversion function between the centralized article reference and the local reference

        Args:
            client: Open connector to the centralized base.
            from_datastore: If True, the conversion is done from the centralized database to the local database.
                If False, the conversion is done from the local base to the centralized base.

        Returns:
            dict: Dictionary containing the conversion function between the centralized article reference and the
            local reference.
        """
        self.ensure_one()
        if not client:
            client = self.of_datastore_connect()
        ds_brand_obj = self.of_datastore_get_model(client, "of.product.brand")
        brand_match = {brand.datastore_brand_id: brand for brand in self.brand_ids}
        ds_brands_data = self.of_datastore_read(ds_brand_obj, list(brand_match.keys()), ["code", "use_prefix"])
        default_code_func = {}
        for ds_brand in ds_brands_data:
            brand = brand_match[ds_brand["id"]]
            brand_from = ds_brand if from_datastore else brand
            brand_to = brand if from_datastore else ds_brand
            if brand_from["use_prefix"] and brand_to["use_prefix"] and brand_from["code"] == brand_to["code"]:
                # Le préfixe est le même : on ne va pas le retirer pour le remettre!
                default_code_func[brand] = lambda code: code
                continue
            if brand_to["use_prefix"]:
                func = f"lambda code: '{brand_to['code']}_'+ code"  # FIXME ?: lambda in safe_eval
            else:
                func = "lambda code: code"  # FIXME ?: lambda in safe_eval
            if brand_from["use_prefix"]:
                func += "[%i:]" % (len(brand_from["code"]) + 1)
            default_code_func[brand] = safe_eval(func)
        return default_code_func
