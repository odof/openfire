# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    of_object = fields.Selection(selection_add=[('sale.order', "Sale Order")])
    of_user_assignment = fields.Selection(
        selection=[
            ('salesman', 'Salesman'),
            ('canvasser', 'Canvasser'),
            ('creator', 'Creator'),
            ('responsible', 'Responsible'),
            ('specific_user', 'Specific user'),
        ],
        string="User assignment",
    )
    of_mandatory = fields.Boolean(
        string="Mandatory", help="Prevent the confirmation of an order if the activity is not carried out"
    )
    of_trigger_type = fields.Selection(
        selection=[('at_creation', "At creation"), ('at_validation', "At validation")],
        string="Trigger",
        default='at_creation',
    )
