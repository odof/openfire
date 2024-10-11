# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get("name"):
            mutation["name"] = name

        if mobile_phone := args.get("mobile_phone"):
            mutation["mobile_phone"] = mobile_phone

        if work_phone := args.get("work_phone"):
            mutation["work_phone"] = work_phone

        if work_email := args.get("work_email"):
            mutation["work_email"] = work_email

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model="res.company", domain=domain)

        if select:
            if select.id:
                odoo_domain += [("id", "=", select.id)]
            if select.name:
                odoo_domain += [("name", "ilike", select.name)]
            if select.mobile_phone:
                odoo_domain += [("mobile_phone", "ilike", select.mobile_phone)]
            if select.work_phone:
                odoo_domain += [("work_phone", "ilike", select.work_phone)]
            if select.work_email:
                odoo_domain += [("work_email", "ilike", select.work_email)]
            if select.company_id:
                odoo_domain += [("company_id", "=", select.company_id)]

        return odoo_domain
