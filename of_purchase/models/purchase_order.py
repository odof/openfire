# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


# Done mais à tester
def _unlink_if_cancelled(self):
    """
    We overload the unlink() function in this way because we need to insert our stock movement test
    between the test on the cancelled state and the super().
    """
    stock_move_obj = self.env["stock.move"]
    for order in self:
        if not order.state == "cancel":
            raise UserError(_("In order to delete a purchase order, you must cancel it first."))
        if self.env.uid != SUPERUSER_ID:
            move_lines = stock_move_obj.search([("origin", "=", order.name), ("state", "!=", "cancel")])
            # L'admin garde la possibilité de supprimer une CF
            if move_lines:
                raise UserError(
                    _(
                        "You cannot delete a supplier order, even if it has been cancelled,"
                        " that has uncancelled inventory movements."
                    )
                )
    return super(Purchase, self)._unlink_if_cancelled()


Purchase._unlink_if_cancelled = _unlink_if_cancelled


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    of_customer_id = fields.Many2one("res.partner", string="Customer")
    of_customer_shipping_id = fields.Many2one(comodel_name="res.partner", string="Customer's delivery address")
    of_customer_shipping_city = fields.Char(
        related="of_customer_shipping_id.city", string="City", store=True, readonly=True, compute_sudo=True
    )
    of_customer_shipping_zip = fields.Char(
        related="of_customer_shipping_id.zip", string="Zip code", store=True, readonly=True, compute_sudo=True
    )
    of_sale_order_id = fields.Many2one("sale.order", string="Original order")
    of_delivery_expected = fields.Char(string="Expected delivery", states={"done": [("readonly", True)]})
    of_sent = fields.Boolean(string="Supplier order sent", copy=False)
    of_project_id = fields.Many2one(comodel_name="account.analytic.account", string="Analytical account")
    of_user_id = fields.Many2one(comodel_name="res.users", string="Technical manager")
    of_reception_state = fields.Selection(
        selection=[("not_received", "Not received"), ("received", "Received")],
        string="Reception status",
        compute="_compute_of_reception_state",
        compute_sudo=True,
        store=True,
    )
    of_delivery_force = fields.Datetime(string="Force scheduled date")

    # Done : À retester
    @api.depends("order_line.move_ids", "order_line.move_ids.picking_id.state")
    def _compute_of_reception_state(self):
        for order in self:
            if order.picking_ids and all(
                [
                    state == "done"
                    for state in order.picking_ids.filtered(lambda p: p.state not in ["cancel"]).mapped("state")
                ]
            ):
                order.of_reception_state = "received"
            else:
                order.of_reception_state = "not_received"

    # cette fonction est Done et testé
    @api.model
    def create(self, vals):
        if self.env["ir.config_parameter"].get_param("of.purchase.of_date_purchase_order"):
            vals["date_order"] = fields.Datetime.now()
        return super(PurchaseOrder, self).create(vals)

    @api.model
    def _prepare_picking(self):
        values = super(PurchaseOrder, self)._prepare_picking()
        values["of_customer_id"] = self.of_customer_id.id
        if self.partner_id:
            addresses = self.partner_id.address_get(["delivery"])
            values["of_partner_shipping_id"] = addresses["delivery"]
        if self.of_customer_id:
            addresses = self.of_customer_id.address_get(["delivery"])
            values["of_customer_shipping_id"] = addresses["delivery"]
        return values

    # Done
    def button_confirm(self):
        super(PurchaseOrder, self).button_confirm()
        if self.env["ir.config_parameter"].get_param("of.purchase.of_recalcul_pa"):
            self._update_purchase_price()

    def button_draft(self):
        """
        Overrides button_draft to reset related stock moves and re-confirm linked operations
        when a purchase order is set back to draft.
        """
        res = super(PurchaseOrder, self).button_draft()
        for order in self:
            # On cherche les mouvements de stock associés à la commande qui sont à l'état annulé
            moves = order.order_line.mapped("move_ids").filtered(lambda m: m.state == "cancel")

            # on cherche des mouvements propagés liés à des règles de stock
            propagated_moves = moves.filtered(lambda m: m.rule_id.group_propagation_option == "propagate")

            # confirmer des mouvements annulés
            for move in propagated_moves:
                if move.state == "cancel":
                    move._action_confirm()

            # ceux qui ont réussi vont remettre l'état du stock.move à waiting
            waiting_moves = propagated_moves.filtered(lambda m: m.state == "waiting").write({"state": "waiting"})

            # le check final pour confirmer que tout est correct
            waiting_moves.check()
        return res

    def button_update_purchase_price(self):
        self._update_purchase_price()

    def _update_purchase_price(self):
        """Updates the seller price and purchase price on
        sales order lines linked to purchase order lines"""
        for order in self:
            for line in order.order_line:
                # On cherche les mouvements de stock associés à la ligne d'achat
                moves = line.move_ids.filtered(lambda m: m.state != "cancel")

                # On cherche les lignes de commande de vente via les mouvements
                sale_lines = moves.mapped("sale_line_id")

                # Mettre à jour les prix d'achat et celui de vente
                sale_lines.write(
                    {
                        "of_seller_price": line.price_unit,
                        "purchase_price": line.price_unit * line.product_id.of_purchase_coeff,
                    }
                )

    def action_view_invoice(self):
        result = super(PurchaseOrder, self).action_view_invoice()
        if not self.invoice_ids:
            result["context"]["default_company_id"] = self.company_id.id
        else:
            result["context"]["default_company_id"] = self.invoice_ids[0].company_id.id
        return result

    def action_set_date_planned(self):
        for order in self:
            order.order_line.update({"date_planned": order.of_delivery_force})

    @api.depends("name", "partner_ref")
    def name_get(self):
        if self._context.get("purchase_amount_total", False):
            # keep the standard if purchase_amount_total is set in the context
            return super(PurchaseOrder, self).name_get()
        result = []
        for po in self:
            name = po.name
            if po.partner_ref:
                name += " (" + po.partner_ref + ")"
            if po.amount_untaxed:
                name += ": " + formatLang(self.env, po.amount_untaxed, currency_obj=po.currency_id)
            result.append((po.id, name))
        return result

    @api.onchange("of_customer_id")
    def _onchange_of_customer_id(self):
        self.ensure_one()
        addresses = self.of_customer_id.address_get(["delivery"])
        self.of_customer_shipping_id = addresses["delivery"]
