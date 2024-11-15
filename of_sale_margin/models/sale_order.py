# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_margin_percent = fields.Float(
        compute="_compute_of_margin_percent", string="Margin %", search="_search_of_margin_percent"
    )
    of_amount_to_invoice = fields.Monetary(
        string="Remains to be invoiced Tax. Excl.", compute="_compute_of_amount_to_invoice_fields", store=True
    )
    of_amount_to_invoice_no_deposit = fields.Monetary(
        string="Remains to be invoiced Tax. Excl. (Deposit excluded)",
        compute="_compute_of_amount_to_invoice_fields",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("margin_percent")
    def _compute_of_margin_percent(self):
        for order in self:
            order.of_margin_percent = order.margin_percent * 100

    def _search_of_margin_percent(self, operator, value):
        """Search method for of_margin_percent field to allow search on margin percent on a non strict basis.

        There is a difference between margin user sees on screen, which is 2 digits rounded, and margin stored in db
        So when the user search for a margin, the search must include "real" values that match the 2 digits rounded
        values searched (example : a 5% margin search must return sale orders with "real" margins
        such as 4,995% and 5,004%)
        """
        top = value + 0.004
        down = value - 0.005
        params = []
        request = "SELECT id FROM sale_order WHERE "
        if operator == "=":
            request += "(100 * margin_percent) >= %s AND " "(100 * margin_percent) <= %s;"
            params = (down, top)
        elif operator == "!=":
            request += "(100 * margin_percent) <= %s OR " "(100 * margin_percent) >= %s;"
            params = (down, top)
        elif operator == ">=":
            request += "(100 * margin_percent) >= %s;"
            params = (down,)
        elif operator == ">":
            request += "(100 * margin_percent) > %s;"
            params = (top,)
        elif operator == "<=":
            request += "(100 * margin_percent) <= %s;"
            params = (top,)
        elif operator == "<":
            request += "(100 * margin_percent) < %s;"
            params = (down,)
        else:
            raise NotImplementedError(_("Search operator %s not implemented for value %s") % (operator, value))
        self.env.cr.execute(request, params)
        ids = [r[0] for r in self.env.cr.fetchall()]
        return [("id", "in", ids)]

    @api.depends("order_line.of_amount_to_invoice")
    def _compute_of_amount_to_invoice_fields(self):
        if categ_id := self.env["ir.config_parameter"].sudo().get_param("of.sale.of_deposit_product_categ_id"):
            categ_id = int(categ_id)
        if deposit_product_id := self.env["ir.config_parameter"].sudo().get_param("sale.default_deposit_product_id"):
            deposit_product_id = int(deposit_product_id)
        for order in self:
            order.of_amount_to_invoice = sum(order.mapped("order_line.of_amount_to_invoice"))
            filtered_lines = order.order_line
            if categ_id:
                filtered_lines = filtered_lines.filtered(lambda li: li.product_id.categ_id.id != categ_id)
            if deposit_product_id:
                filtered_lines = filtered_lines.filtered(lambda li: li.product_id.id != deposit_product_id)
            order.of_amount_to_invoice_no_deposit = sum(filtered_lines.mapped("of_amount_to_invoice"))

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override to make `margin_percent` non-searchable.
        This is because the search is now done on the computed field of the
        sale order, which is not stored in the database.

        This is a avoid the following misundertanding with the two fields displayed in the dropdown menu for
        searching.
        """
        res = super().fields_get(allfields, attributes=attributes)
        for field in res:
            if field != "margin_percent":
                continue
            res[field]["searchable"] = False
        return res
