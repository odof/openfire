from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    of_due_date = fields.Date(string=u"Date d'échéance")
