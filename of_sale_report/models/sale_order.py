from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_installation_date = fields.Date("Date de pose prévisionnelle")
