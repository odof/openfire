# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFImportBrandLine(models.TransientModel):
    _name = "of.datastore.import.brand.line"

    wizard_id = fields.Many2one(comodel_name="of.datastore.import.brand")
    name = fields.Char(required=True)
    datastore_brand_id = fields.Integer(string="Centralized ID")
    code = fields.Char(required=True, readonly=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="Supplier", domain=[("is_supplier", "=", True)])
    product_categ_id = fields.Many2one(comodel_name="product.category", string="Category")
    logo = fields.Binary()
    update_note = fields.Text(string="Update notes")
    state = fields.Selection(selection=[("do", "Included"), ("dont", "Excluded"), ("done", "Exists")])

    def action_button_inverse(self):
        new_state = {
            "do": "dont",
            "dont": "do",
            "done": "done",
        }
        for line in self:
            line.state = new_state[line.state]
        return {
            "type": "ir.actions.act_window",
            "res_model": "of.datastore.import.brand",
            "res_id": line.wizard_id.id,
            "view_mode": "form",
            "target": "new",
        }
