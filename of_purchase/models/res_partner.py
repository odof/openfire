# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_count_receptions = fields.Integer(string="Receptions", compute="_compute_of_count_receptions")

    def _compute_of_count_receptions(self):
        picking_obj = self.env["stock.picking"]
        for partner in self:
            partner.of_count_receptions = picking_obj.search_count(
                [("of_customer_id", "=", partner.id), ("of_location_usage", "=", "supplier")]
            )

    def _compute_purchase_order_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        super(ResPartner, self)._compute_purchase_order_count()
        all_partners = self.with_context(active_test=False).search([("id", "child_of", self.ids)])
        all_partners.read(["parent_id"])

        purchase_order_groups = self.env["purchase.order"]._read_group(
            domain=[("partner_id", "in", all_partners.ids)], fields=["partner_id"], groupby=["partner_id"]
        )
        partners = self.browse()
        for group in purchase_order_groups:
            partner = self.browse(group["partner_id"][0])
            while partner:
                if partner in self:
                    partner.purchase_order_count = group["partner_id_count"]
                    partners |= partner
                partner = partner.parent_id
        (self - partners).purchase_order_count = 0

    def _compute_supplier_invoice_count(self):
        super(ResPartner, self)._compute_supplier_invoice_count()
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([("id", "child_of", self.ids)])
        all_partners.read(["parent_id"])

        supplier_invoice_groups = self.env["account.move"]._read_group(
            domain=[("partner_id", "in", all_partners.ids), ("move_type", "=", "in_refund")],
            fields=["partner_id"],
            groupby=["partner_id"],
        )
        partners = self.browse()
        for group in supplier_invoice_groups:
            partner = self.browse(group["partner_id"][0])
            while partner:
                if partner in self:
                    partner.supplier_invoice_count += group["partner_id_count"]
                    partners |= partner
                partner = partner.parent_id
        (self - partners).supplier_invoice_count = 0

    def action_view_picking(self):
        action = self.env.ref("of_purchase.of_purchase_open_picking").read()[0]
        action["domain"] = [("of_customer_id", "in", self._ids)]
        return action
