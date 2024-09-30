# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    of_equipment_id = fields.Many2one(comodel_name="of.equipment", string="Equipment")

    def action_create_equipment(self, picking=None):
        """Create an equipment for each lot of the picking."""
        if picking is None or not picking.partner_id:
            return

        equipment_obj = self.env["of.equipment"]
        equipment_obj.create([lot._get_new_equipment_values(picking) for lot in self])

    def _get_new_equipment_values(self, picking):
        self.ensure_one()
        return {
            "name": f"{self.name} - {picking.partner_id.name}",
            "customer_id": picking.partner_id.id,
            "site_address_id": picking.partner_id.id,
            "product_id": self.product_id.id,
            "brand_id": self.product_id.brand_id.id,
            "product_category_id": self.product_id.categ_id.id,
            "installation_date": fields.Date.today(),
            "service_date": picking.sale_id and picking.sale_id.date_order,
            "lot_id": self.id,
        }
