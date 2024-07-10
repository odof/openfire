# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleOrderConfirmation(models.TransientModel):
    """Transient model that allows to add a confirmation step before validating a sale order"""

    _name = 'of.sale.order.confirmation'
    _description = "Sale Order Confirmation"

    order_id = fields.Many2one(comodel_name='sale.order')
    confirmation_date = fields.Datetime(string="Confirmation date", default=fields.Datetime.now())

    def action_bouton_validate(self):
        action, need_interruption = self.env['of.sale.order.verification'].do_verification(self.order_id)
        if need_interruption:
            return action
        self.order_id.of_date_order = self.confirmation_date
        res = self.order_id.action_confirm()
        return action or res
