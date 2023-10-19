from odoo import api, fields, models


class OfSaleOrderVerification(models.TransientModel):
    _inherit = 'of.sale.order.verification'

    type = fields.Selection(selection_add=[("date_de_pose", "Date de pose prévisionnelle")], string="Type")
    date = fields.Date(string="Date de pose")
