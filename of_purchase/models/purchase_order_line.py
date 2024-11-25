# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_round

import odoo.addons.decimal_precision as dp


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    of_total_stock_qty = fields.Float(
        string="Total stock", digits=dp.get_precision("Product Unit of Measure"), compute="_compute_of_stock_qty"
    )
    of_available_stock_qty = fields.Float(
        string="Available stock.", digits=dp.get_precision("Product Unit of Measure"), compute="_compute_of_stock_qty"
    )
    of_theoretical_stock_qty = fields.Float(
        string="Theoretical stock.",
        digits=dp.get_precision("Product Unit of Measure"),
        compute="_compute_of_stock_qty",
        help="If a stock rule is defined for the product with a forecast cut-off date, the Theoretical inventory "
        "is calculated on this date; otherwise the theoretical stock calculated is the total theoretical stock of the product",
    )
    of_reserved_qty = fields.Float(
        string="Qty reserved", digits=dp.get_precision("Product Unit of Measure"), compute="_compute_of_stock_qty"
    )

    # Done mais à tester après la correction de bouton confirm!!!!!!!
    @api.depends("product_id", "order_id.picking_type_id", "order_id.picking_type_id.default_location_dest_id")
    def _compute_of_stock_qty(self):
        for line in self:
            if line.order_id.picking_type_id.default_location_dest_id:
                location = line.order_id.picking_type_id.default_location_dest_id
                product_context = dict(self._context, location=location.id)

                # Stock total
                line.of_total_stock_qty = line.product_id.with_context(product_context).qty_available

                # Stock dispo
                domain_quant = [("product_id", "=", line.product_id.id), ("reserved_quantity", "=", 0.0)]
                domain_quant += line.product_id.with_context(product_context)._get_domain_locations()[0]
                quants = self.env["stock.quant"].search(domain_quant)
                line.of_available_stock_qty = float_round(
                    sum(quants.mapped("available_quantity")), precision_rounding=0.01
                )
                # precision_rounding=line.product_id.uom_id.rounding

                # Stock théorique
                orderpoints = self.env["stock.warehouse.orderpoint"].search(
                    [("product_id", "=", line.product_id.id)], limit=1
                )
                if orderpoints and orderpoints.of_forecast_limit:
                    product_context["of_to_date_expected"] = (
                        datetime.today() + relativedelta(days=orderpoints.of_forecast_period)
                    ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                line.of_theoretical_stock_qty = line.product_id.with_context(product_context).virtual_available

                # Qté(s) réservée(s)
                stock_moves = line.mapped("move_ids")
                if stock_moves:
                    domain_quant = [("product_id", "=", line.product_id.id), ("reserved_quantity", "!=", 0)]
                    domain_quant += line.product_id.with_context(product_context)._get_domain_locations()[0]
                    quants = self.env["stock.quant"].search(domain_quant)
                    line.of_reserved_qty = float_round(
                        sum(quants.mapped("reserved_quantity")), precision_rounding=line.product_id.uom_id.rounding
                    )
                else:
                    line.of_reserved_qty = 0

            else:
                line.of_total_stock_qty = 0
                line.of_available_stock_qty = 0
                line.of_theoretical_stock_qty = 0
                line.of_reserved_qty = 0

    @api.model
    def _prepare_purchase_order_line_from_procurement(
        self, product_id, product_qty, product_uom, company_id, values, po
    ):
        res = super()._prepare_purchase_order_line_from_procurement(
            product_id, product_qty, product_uom, company_id, values, po
        )

        desc_option = self.env["ir.config_parameter"].sudo().get_param("purchase.of_description_as_order_setting")
        if desc_option and values.get("sale_line_id"):
            sale_line = self.env["sale.order.line"].browse(values["sale_line_id"])
            product_lang = product_id.with_context(
                lang=po.partner_id.lang,
                partner_id=po.partner_id.id,
            )

            name = sale_line.name or res.get("name", "")
            if product_lang.description_purchase:
                name += f"\n{product_lang.description_purchase}"
            res["name"] = name

        if values.get("product_description_variants"):
            res["name"] += f"\n{values['product_description_variants']}"

        return res

    # def write(self, vals):
    #     res = super(PurchaseOrderLine, self).write(vals)
    #     if "price_unit" in vals:
    #         # On répercute le changement de prix pour la valorisation de l'inventaire s'il y a lieu
    #         moves = self.mapped("move_ids")
    #         if moves:
    #             moves.write({"price_unit": vals["price_unit"]})
    #             quants = moves.mapped("quant_ids")
    #             if quants:
    #                 quants.sudo().write({"cost": vals["price_unit"]})
    #     return res
