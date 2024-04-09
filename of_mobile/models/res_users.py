# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_fcm_token_ids = fields.One2many(comodel_name='of.fcm.device.token', inverse_name='user_id', string=u"FCM Tokens")

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if fcm_tokens := args.get('fcm_tokens'):
            mutation['of_fcm_token_ids'] = x2many(self=self, model='of.fcm.device.token', input=fcm_tokens)

        return mutation
