# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if 'of_used_for_phone' in args.keys():
            mutation['of_used_for_phone'] = args['of_used_for_phone']

        return mutation
