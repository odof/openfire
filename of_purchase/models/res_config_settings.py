# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_description_as_order_setting = fields.Selection(
        selection=[
            ("0", "Item description as entered in the catalogue"),
            ("1", "Item description as entered in the quotation"),
        ],
        string="(OF) Product description",
        help="Choose the type of description displayed in the supplier order.\n"
        "This also affects printable documents.",
    )

    group_purchase_order_line_display_stock_info = fields.Boolean(
        string="(OF) Stock information",
        implied_group="of_purchase.group_purchase_order_line_display_stock_info",
        group="base.group_portal,base.group_user,base.group_public",
        help="Displays stock information in order line",
    )

    of_date_purchase_order = fields.Selection(
        selection=[("0", "Standard"), ("1", "Date du jour")], string="(OF) Supplier order dates "
    )
    of_recalcul_pa = fields.Boolean(string="(OF) Automatic recalculation of purchase prices on order lines")

    def set_description_as_order_defaults(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .set_param("of.purchase.of_description_as_order_setting", self.of_description_as_order_setting)
        )

    def set_of_date_purchase_order_defaults(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .set_param("of.purchase.of_date_purchase_order", self.of_date_purchase_order)
        )

    def set_of_recalcul_pa_defaults(self):
        return self.env["ir.config_parameter"].sudo().set_param("of.purchase.of_recalcul_pa", self.of_recalcul_pa)

    def get_description_as_order_defaults(self):
        return self.env["ir.config_parameter"].sudo().get_param("of.purchase.of_description_as_order_setting")

    def get_of_date_purchase_order_defaults(self):
        return self.env["ir.config_parameter"].sudo().get_param("of.purchase.of_date_purchase_order")

    def get_of_recalcul_pa_defaults(self):
        return self.env["ir.config_parameter"].sudo().get_param("of.purchase.of_recalcul_pa")

    def set_values(self):
        super().set_values()
        self.set_description_as_order_defaults()
        self.set_of_date_purchase_order_defaults()
        self.set_of_recalcul_pa_defaults()

    def get_values(self):
        res = super().get_values()
        of_description_as_order_setting = self.get_description_as_order_defaults()
        of_date_purchase_order = self.get_of_date_purchase_order_defaults()
        of_recalcul_pa = self.get_of_recalcul_pa_defaults()
        res.update(
            {
                "of_description_as_order_setting": of_description_as_order_setting,
                "of_date_purchase_order": of_date_purchase_order,
                "of_recalcul_pa": of_recalcul_pa,
            }
        )
        return res
