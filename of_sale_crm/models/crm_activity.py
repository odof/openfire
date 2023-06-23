# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CRMActivity(models.Model):
    _inherit = 'crm.activity'

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
    of_mandatory = fields.Boolean(
        string="Mandatory", help="Prevent the confirmation of an order if the activity is not carried out"
    )
    of_trigger_type = fields.Selection(
        selection=[('at_creation', "At creation"), ('at_validation', "At validation")],
        string="Trigger",
        default='at_creation',
    )

    @api.onchange('of_object')
    def _onchange_of_object(self):
        if self.of_object == 'sale.order':
            self.of_user_id = False
        else:
            self.of_user_assignment = False
            self.of_trigger_type = False
        return super()._onchange_of_object()

    @api.onchange('of_user_assignment')
    def _onchange_of_user_assignment(self):
        if self.of_user_assignment != 'specific_user':
            self.of_user_id = False

    @api.onchange('of_compute_date_id')
    def _onchange_of_compute_date_id(self):
        self.of_automatic_recompute = self.of_compute_date_id.model == 'sale.order'
        # :todo: Voir comment gérer ça.
        #   Soit ajouter un champ "code" pour identifier les types de dates, soit ajouter un champ "force_trigger_type"
        if self.of_compute_date == 'confirmation_date':
            self.of_trigger_type = 'at_validation'
        return super()._onchange_of_compute_date_id()
