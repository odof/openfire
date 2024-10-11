# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    of_fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position", string="Fiscal position", company_dependent=True
    )
    of_payment_term_id = fields.Many2one(comodel_name="account.payment.term", string="Terms of payment")
    of_custom_document_ids = fields.Many2many(comodel_name="of.custom.document", string="Documents")
