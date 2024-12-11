# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
from simplejson import JSONDecodeError

from odoo import _, fields, models
from odoo.exceptions import UserError


class OFDatastoreBrandAskWizard(models.TransientModel):
    _name = "of.datastore.brand.ask.wizard"

    fee = fields.Float(related="datastore_brand_id.fee", string="Additional cost")
    fee2 = fields.Float(related="datastore_brand_id.fee", string="Additional cost 2")
    action = fields.Selection(
        selection=[("connect", "Connection"), ("disconnect", "Disconnect"), ("cancel", "Cancellation")], required=True
    )
    brand_id = fields.Many2one(
        comodel_name="of.product.brand", related="datastore_brand_id.brand_id", string="Brand to associate"
    )
    datastore_brand_id = fields.Many2one(
        comodel_name="of.datastore.brand", string="Product datastore brand", required=True, ondelete="cascade"
    )

    # Champs relationnels pour faciliter la lecture en xmlrpc depuis la base de gestion OpenFire
    ds_brand_id = fields.Integer(related="datastore_brand_id.datastore_brand_id")
    ds_db_name = fields.Char(related="datastore_brand_id.db_name")

    def action_button_process(self):
        """We inform the OpenFire management database that there is a request to process.
        This base will fetch the information directly from the wizard in xmlrpc.
        It is therefore impossible to take advantage of the public route to send a non-legitimate request."""
        openfire_url = self.env["ir.config_parameter"].get_param("of.openfire.database.url")
        response = requests.post(
            url=f"{openfire_url}/brand/request",
            params={"dbname": self._cr.dbname, "request_id": self.id},
            timeout=60,
        )
        if response.status_code != requests.codes.ok:
            try:
                message = response.json()
            except JSONDecodeError:
                message = ""
            raise UserError(_("Error processing request : %(code)s - %(msg)s", code=response.status_code, msg=message))
