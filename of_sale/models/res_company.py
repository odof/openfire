# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    show_manufacturer_description = fields.Selection(
        [
            ("no", "Do not show"),
            ("sales", "In Sales Orders"),
            ("invoices", "In Invoices"),
            ("both", "In Sales Orders and Invoices"),
        ],
        string="Show manufacturer descriptions",
        default="both",
        help="The manufacturer's description of an item will be added to the item description in the documents.",
    )
