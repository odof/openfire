# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one

logger = logging.getLogger(__name__)


class OFResPartnerPhone(models.Model):
    _inherit = 'of.res.partner.phone'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if type := args.get('type'):
            mutation['type'] = type

        if number_display := args.get('number_display'):
            mutation['number_display'] = number_display

        if title := args.get('title'):
            mutation['title_id'] = many2one(self=self, model='res.partner.title', input=title)

        return mutation
