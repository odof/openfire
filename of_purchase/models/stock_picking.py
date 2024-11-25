# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    of_customer_id = fields.Many2one("res.partner", string="Customer")
    of_customer_shipping_id = fields.Many2one("res.partner", string="Customer's delivery address")
    of_customer_shipping_city = fields.Char(
        related="of_customer_shipping_id.city", string="City", store=True, readonly=True, compute_sudo=True
    )
    of_customer_shipping_zip = fields.Char(
        related="of_customer_shipping_id.zip", string="Zip code", store=True, readonly=True, compute_sudo=True
    )
    of_partner_shipping_id = fields.Many2one("res.partner", string="Partner's delivery address")
    of_partner_shipping_city = fields.Char(
        related="of_partner_shipping_id.city", string="City", store=True, readonly=True, compute_sudo=True
    )
    of_partner_shipping_zip = fields.Char(
        related="of_partner_shipping_id.zip", string="Zip code", store=True, readonly=True, compute_sudo=True
    )
    # Permet de cacher le champ of_customer_id si pas sur BR
    of_location_usage = fields.Selection(related="location_id.usage")
    of_user_id = fields.Many2one(comodel_name="res.users", string="Technical manager")

    @api.onchange("of_customer_id")
    def _onchange_of_customer_id(self):
        self.ensure_one()
        addresses = self.of_customer_id.address_get(["delivery"])
        self.of_customer_shipping_id = addresses["delivery"]

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        self.ensure_one()
        addresses = self.partner_id.address_get(["delivery"])
        self.of_partner_shipping_id = addresses["delivery"]
