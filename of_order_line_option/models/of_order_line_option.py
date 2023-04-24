# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OfSaleLineOption(models.Model):
    _name = 'of.order.line.option'
    _description = "Option for sale and purchase order lines"

    name = fields.Char(required=True)
    purchase_price_update = fields.Boolean(string="Alters purchase price")
    purchase_price_update_type = fields.Selection(
        selection=[
            ('fixed', "Set amount"),
            ('percent', "Percentage"),
        ],
        string="Purchase price alteration type",
        default='fixed',
    )
    purchase_price_update_value = fields.Float(string="Purchase price alteration value")
    sale_price_update = fields.Boolean(string="Alters sale price")
    sale_price_update_type = fields.Selection(
        selection=[
            ('fixed', "Set amount"),
            ('percent', "Percentage"),
        ],
        string="Sale price alteration type",
        default='fixed',
    )
    sale_price_update_value = fields.Float(string="Sale price alteration value")
    description_update = fields.Text(string="Order line description")
