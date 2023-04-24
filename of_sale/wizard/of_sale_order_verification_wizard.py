# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfSaleOrderVerification(models.TransientModel):
    """Base Transient model to do specific verifications on Sale Order confirmation."""

    _name = 'of.sale.order.verification'
    _description = __doc__

    message = fields.Text(string="Message")
    type = fields.Selection(selection=[], string="Type")
    order_id = fields.Many2one(comodel_name='sale.order', string="Sale order")

    @api.model
    def do_verification(self, order):
        """Default method to do specific verifications on Sale Order.
        To override in inherited models to add needed verifications.

        Should updates the context that will be used to open the wizard.

        Exemple of using :

        .. code-block:: python

            class MySaleOrderVerification(models.TransientModel):
                _inherit = 'of.sale.order.verification'

                def do_verification(self, order):
                    context = self.env.context.copy()
                    context.update({
                        'default_type': 'my_selection_value',
                        'default_message': "My message",
                    })
                    return self.with_context(context).action_open_wizard(), self.need_interruption(order)

        :param order: Sale Order to verify
        :return: (action to open the wizard, need_interruption boolean)"""
        return False, False

    @api.model
    def need_interruption(self, order=False):
        """Default method to check if the verification must interrupt the validation process.
        To override in inherited models to add needed interruptions"""
        return False

    @api.model
    def action_open_wizard(self, title="Informations"):
        """Return action to open the wizard and interrupt the validation process if needed.

        :param bool need_interruption: True if the validation process must be interrupted
        :param str title: Title of the action to open, defaults to "Informations"
        :return: (action to open the wizard and interrupt the validation process, need_interruption boolean)
        """
        context = self.env.context.copy()
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'of.sale.order.verification',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def validate_step(self):
        """
        Action to inherit if the current step requires an additional action.
        Exemple:
            We do the verification on a field of th sale order, if it is not filled we want to fill it in this
            wizard, then this function allows you to write on the command before going to the next step.
        """
        pass

    def action_button_next_step(self):
        self.validate_step()
        action, need_interruption = self.do_verification(self.order_id)
        return action

    def action_button_skip_validation(self):
        action, need_interruption = self.do_verification(self.order_id)
        return action
