# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.base.models.res_partner import WARNING_HELP


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_warn = fields.Selection(related="invoice_warn", help=WARNING_HELP, readonly=True)
    sale_warn_msg = fields.Text(related="invoice_warn_msg", readonly=True)
    of_is_sale_warn = fields.Boolean(string="Sales warning")
    of_invoice_policy = fields.Selection(
        selection=[("order", "Ordered quantities"), ("delivery", "Delivered quantities")],
        string="Invoicing policy",
    )
    of_last_order_date = fields.Date(string="Last quote date", compute="_compute_of_last_order_date", compute_sudo=True)

    @api.depends("of_is_sale_warn")
    def _compute_of_is_warn(self):
        has_warn = self.filtered("of_is_sale_warn")
        for partner in has_warn:
            partner.of_is_warn = True
        partners_left = self - has_warn
        super(ResPartner, partners_left)._compute_of_is_warn()

    def _compute_of_last_order_date(self):
        for partner in self:
            last_order = self.env["sale.order"].search([("partner_id", "=", partner.id)], order="id desc", limit=1)
            partner.of_last_order_date = last_order.date_order if last_order else False
