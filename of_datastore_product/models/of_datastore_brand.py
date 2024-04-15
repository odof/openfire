# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
from requests.exceptions import JSONDecodeError

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


class OFDatastoreBrand(models.Model):
    _name = "of.datastore.brand"
    _description = "Brands accessible via Product Datastore (PD)"
    _inherit = "mail.thread"
    _order = "name"

    datastore_brand_id = fields.Integer(string="Centralized ID", help="Brand ID based on supplier")
    db_name = fields.Char(string="Supplier database")
    name = fields.Char(string="Wording", required=True)
    logo = fields.Binary(attachment=True)
    update_date = fields.Date(string="Update date", readonly=True)
    is_partner_managed = fields.Boolean(
        string="Partner supplier",
        help="If the supplier is a partner, he is responsible for updating his prices.\n"
        "Otherwise, the update is carried out by OpenFire and incurs an additional cost.",
    )
    fee = fields.Float(string="Additional cost (monthly)")
    state = fields.Selection(
        selection=[
            ("available", "Available"),
            ("pending_in", "Connection request pending"),
            ("connected", "Connected"),
            ("pending_out", "Disconnect request pending"),
        ],
        required=True,
        tracking=True,
    )
    brand_id = fields.Many2one(comodel_name="of.product.brand", string="Associated brand", ondelete="restrict")

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def write(self, vals):
        if self._uid != SUPERUSER_ID and any(field in ("is_partner_managed", "fee", "name") for field in vals):
            raise UserError(_("You are trying to modify protected fields"))
        return super().write(vals)

    # -------------------------------------------------------------------------
    # Actions methods
    # -------------------------------------------------------------------------

    def action_granted(self, login, password):
        """
        Action called by admin account (from a remote_database) to accept the brand's connection to the Product
        Datastore
        """
        self.ensure_one()
        if not self.brand_id:
            raise UserError(_("The application is not associated with a brand"))
        if self.brand_id.datastore_supplier_id:
            raise UserError(_("The brand is already connected"))

        supplier_obj = self.env["of.datastore.supplier"]
        supplier = supplier_obj.search([("db_name", "=", self.db_name)]) or supplier_obj.create(
            {
                "db_name": self.db_name,
                "server_address": f"https://{self.db_name}.openfire.fr",  # noqa
                "login": login,
                "password": password,
            }
        )

        self.brand_id.write(
            {
                "datastore_supplier_id": supplier.id,
                "datastore_brand_id": self.datastore_brand_id,
            }
        )

        # We empty the of_datastore_res_id field of the items of brand newly linked to the centralized price list.
        self.env["product.product"].search(
            [("brand_id", "=", self.brand_id.id), ("of_datastore_res_id", "!=", False)]
        ).write({"of_datastore_res_id": False})
        self.env["product.template"].search(
            [("brand_id", "=", self.brand_id.id), ("of_datastore_res_id", "!=", False)]
        ).write({"of_datastore_res_id": False})

        self.write({"state": "connected"})
        return True

    def action_revoked(self):
        """
        Action called by the admin account (from a remote_database) to cut the brand's connection to the Product
        Datastore
        """
        brands = self.mapped("brand_id")
        brands.write(
            {
                "datastore_supplier_id": False,
                "datastore_brand_id": False,
            }
        )
        self.env["product.product"].search(
            [("brand_id", "in", brands.ids), ("of_datastore_res_id", "!=", False)]
        ).write({"of_datastore_res_id": False})
        self.env["product.template"].search(
            [("brand_id", "in", brands.ids), ("of_datastore_res_id", "!=", False)]
        ).write({"of_datastore_res_id": False})
        self.write({"state": "available"})
        return True

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @api.model
    def cron_update_brands(self):
        """Update the list of brands accessible via the Product Datastore"""
        icp_obj = self.env["ir.config_parameter"]
        openfire_url = icp_obj.get_param("of.openfire.database.url")
        last_update = icp_obj.get_param("of.datastore.brand.last.update")

        response = requests.post(
            url=f"{openfire_url}/brand/list",
            params={"dbname": self._cr.dbname, "since_dt": last_update or ""},
            timeout=10,
        )
        if response.status_code != requests.codes.ok:
            try:
                message = response.json()
            except JSONDecodeError as e:
                message = e.args[0]
            raise UserError(
                _("Error processing request : %(code)s - %(message)s", code=response.status_code, message=message)
            )

        data = response.json()

        # Update or create brands
        local_brands_dict = {(brand.db_name, brand.datastore_brand_id): brand for brand in self.search([])}
        for brand_data in data:
            local_brand = local_brands_dict.pop((brand_data["db_name"], brand_data["datastore_brand_id"]), False)
            if "name" in brand_data:
                if local_brand:
                    local_brand.write(brand_data)
                else:
                    brand_data["state"] = "available"
                    self.create(brand_data)

        # Remove brands that no longer exist
        if to_remove_ids := [brand.id for brand in local_brands_dict.values()]:
            self.browse(to_remove_ids).unlink()

        # Update the last update date
        icp_obj.set_param("of.datastore.brand.last.update", fields.Date.today())

        # If there are connected brands but not linked to a brand in the management base, we try to associate them
        for brand in self.env["of.product.brand"].search(
            [("datastore_brand_id", "!=", False), ("datastore_brand_request_ids", "=", False)]
        ):
            if datastore_brand := self.search(
                [
                    ("db_name", "=", brand.datastore_supplier_id.db_name),
                    ("datastore_brand_id", "=", brand.datastore_brand_id),
                ],
                limit=1,
            ):
                if datastore_brand.brand_id:
                    raise UserError(
                        _(
                            "A centralized mark has several possible matches :"
                            " %(ds_name)s vs %(ds_brand_name)s and %(brand_name)s",
                            ds_name=datastore_brand.name,
                            ds_brand_name=datastore_brand.brand_id.name,
                            brand_name=brand.name,
                        )
                    )
                datastore_brand.write(
                    {
                        "brand_id": brand.id,
                        "state": "connected",
                    }
                )
