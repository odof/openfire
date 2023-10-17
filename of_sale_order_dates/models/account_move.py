# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    of_technical_visit_date = fields.Date(string="Technical visit date")

    def pdf_technical_visit_info(self):
        self.ensure_one()
        return self.company_id.pdf_technical_visit_info_move
