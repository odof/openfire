# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..models.tools import _get_list_from_parameter


class DisableIPv6Context:
    """Poujoulat isn't IPV6 friendly so we are deactivating it for all requests we are sending to them"""

    def __enter__(self):
        self.original_ipv6 = requests.packages.urllib3.util.connection.HAS_IPV6
        requests.packages.urllib3.util.connection.HAS_IPV6 = False

    def __exit__(self, *args):
        requests.packages.urllib3.util.connection.HAS_IPV6 = self.original_ipv6


class OFPoujoulatCartWizard(models.TransientModel):
    _name = "of.poujoulat.cart.wizard"
    _description = "Wizard to send PO cart to Poujoulat"

    purchase_id = fields.Many2one(comodel_name="purchase.order")
    line_ids = fields.One2many(comodel_name="of.poujoulat.cart.item.wizard", inverse_name="wizard_id")
    message = fields.Text(readonly=True, compute="_compute_message")
    sent = fields.Boolean(string="Sent to CatEstimate")
    has_error = fields.Boolean(string="Sending error")

    @api.depends("line_ids")
    def _compute_message(self):
        """Computes the message to be displayed about the
        items . This message indicates which
        brands have been configured and which items will not be sent due to missing information.
        """

        brand_ids = _get_list_from_parameter(self, "of.connector.poujoulat.brand_ids")

        brands = self.env["of.product.brand"].browse(brand_ids).exists()
        message = _("Only items from the configured brands will be sent. List of brands:\n%s\n") % "\n".join(
            f"* {brand.name}" for brand in brands
        )
        for record in self:
            final_message = [message]
            if products := [line.product_id for line in record.line_ids if not line._get_estimate_values()]:
                final_message.extend(
                    [
                        _("The following items will not be sent because informations are missing :\n%s\n")
                        % "\n".join(f"* {product.display_name}" for product in products)
                    ]
                )
            record.message = "\n".join(final_message)

    def action_button_send_cart(self):
        """
        Sends the cart's contents to the configured Poujoulat server.

        Returns:
            dict: A redirect action to a new URL if the server returns a `redirectionUrl`.
                Otherwise, no action is taken.
        """
        self.ensure_one()
        poujoulat_url, redirect_url = self._fetch_configuration()
        values = self._prepare_data()
        with DisableIPv6Context():
            response_data = self._send_request(poujoulat_url, values)
        return self._process_response(redirect_url, response_data)

    def _fetch_configuration(self):
        """
        Retrieves the configured Poujoulat server address and redirect URL.

        Returns:
            tuple: Contains the Poujoulat server URL and redirect URL.
        """
        ir_config_parameter = self.env["ir.config_parameter"]
        poujoulat_url = ir_config_parameter.get_param("of.connector.poujoulat.host")
        redirect_url = ir_config_parameter.get_param("of.connector.poujoulat.url_redirect", default="")

        if not poujoulat_url:
            raise ValidationError(_("No server address has been configured for the poujoulat connector."))

        return poujoulat_url, redirect_url

    def _prepare_data(self):
        """
        Prepares the data to be sent to the Poujoulat server.

        Returns:
            dict: containing the estimate lines.
        """
        values = {"estimateLines": []}
        for line in self.line_ids:
            vals = line._get_estimate_values()
            if line.quantity and vals:
                values["estimateLines"].append(vals)

        return values

    def _send_request(self, poujoulat_url, values):
        """
        Sends a POST request to the Poujoulat server with the prepared payload.

        Args:
            poujoulat_url (str): The URL of the Poujoulat server.
            values (dict): The payload containing the estimate lines.
            redirect_url (str): The redirect URL to be used if a redirection is provided.

        Returns:
            dict: Response data
        """

        if not poujoulat_url or not values:
            raise ValidationError(_("Missing data to send to the Poujoulat server."))

        response = {}
        try:
            response = requests.post(
                poujoulat_url, headers={"Content-Type": "application/json"}, data=json.dumps(values), timeout=20
            )
            data = response.json()
            # si l'envoi est réussi (c'est-à-dire que le serveur répond positivement),
            # la fonction met à jour le statut de la commande d'achat pour indiquer qu'elle a été envoyée avec succès.
            if response.status_code == 200:
                self.purchase_id.write({"of_poujoulat_sent": True, "of_poujoulat_error": False})
                self.sent = True
            else:
                error_message = _("Error code [%(code)s]\n%(text)s", code=response.status_code, text=response.text)
                self.purchase_id.write({"of_poujoulat_error": error_message})
                self.has_error = True
        except Exception as e:
            error_message = _("Error: %s") % str(e)
            self.purchase_id.write({"of_poujoulat_error": error_message})
            self.has_error = True
        return data

    def _process_response(self, redirect_url=False, response_data=False):
        if not redirect_url or not response_data:
            return {"type": "ir.actions.act_window_close"}

        if response_redirection_url := response_data["data"].get("redirectionUrl"):
            if not redirect_url.endswith("/"):
                redirect_url += "/"
            final_url = f"{redirect_url}{response_redirection_url}"
            return {"type": "ir.actions.act_url", "url": final_url, "target": "new"}
        return {"type": "ir.actions.act_window_close"}
