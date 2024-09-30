# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _prepare_mutation_values(self, input, **args):
        mutation = {}

        if name := args.get("name"):
            mutation["name"] = name

        if partner := args.get("partner"):
            mutation["partner_id"] = many2one(self=self, model="res.partner", input=partner)

        if "lines" in args:
            mutation["invoice_line_ids"] = x2many(self=self, model="account.move.line", input=args.get("lines"))

        if fiscal_position := args.get("fiscal_position"):
            mutation["fiscal_position_id"] = many2one(self=self, model="account.fiscal.position", input=fiscal_position)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="account.move.line", domain=domain)

        if select:
            if select.id:
                odoo_domain += [("id", "=", select.id)]
            if select.name:
                odoo_domain += [("name", "ilike", select.name)]

        return odoo_domain
