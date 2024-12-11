# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFImportBrand(models.TransientModel):
    _name = "of.datastore.import.brand"

    datastore_supplier_id = fields.Many2one(comodel_name="of.datastore.supplier", string="Connector")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Supplier", domain=[("is_supplier", "=", True)])
    product_categ_id = fields.Many2one(comodel_name="product.category", string="Category")
    line_ids = fields.One2many(comodel_name="of.datastore.import.brand.line", inverse_name="wizard_id", string="Brands")

    def action_button_import_brands(self):
        self.ensure_one()
        brand_obj = self.env["of.product.brand"]
        for line in self.line_ids:
            if line.state != "do":
                continue
            brand_obj.create(
                {
                    "name": line.name,
                    "code": line.code,
                    "logo": line.logo,
                    "partner_id": (line.partner_id or self.partner_id).id,
                    "of_import_categ_id": (line.product_categ_id or self.product_categ_id).id,
                    "datastore_supplier_id": self.datastore_supplier_id.id,
                    "datastore_brand_id": line.datastore_brand_id,
                }
            )
