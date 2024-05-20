# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

logger = logging.getLogger(__name__)


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='account.fiscal.position', domain=domain)

        if select:
            if select.tax_type_use:
                odoo_domain += [('tax_ids.tax_src_id.type_tax_use', '=', select.tax_type_use.value)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
