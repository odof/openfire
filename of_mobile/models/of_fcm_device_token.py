# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFFCMDeviceToken(models.Model):
    _name = 'of.fcm.device.token'
    _rec_name = 'token'

    token = fields.Char(string="Token", required=True)
    user_id = fields.Many2one(comodel_name='res.users', string="User")

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if token := args.get('token'):
            mutation['token'] = token

        if user := args.get('user'):
            mutation['user_id'] = user

        return mutation
