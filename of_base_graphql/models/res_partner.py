# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}
        if name := args.get("name"):
            mutation["name"] = name

        if street := args.get("street"):
            mutation["street"] = street

        if street2 := args.get("street2"):
            mutation["street2"] = street2

        if city := args.get("city"):
            mutation["city"] = city

        if zzip := args.get("zip"):
            mutation["zip"] = zzip

        if email := args.get("email"):
            mutation["email"] = email

        if write_date := args.get("write_date"):
            mutation["write_date"] = write_date

        if create_date := args.get("create_date"):
            mutation["create_date"] = create_date

        if company_type := args.get("company_type"):
            mutation["company_type"] = company_type

        if partner_latitude := args.get("partner_latitude"):
            mutation["partner_latitude"] = partner_latitude

        if partner_longitude := args.get("partner_longitude"):
            mutation["partner_longitude"] = partner_longitude

        if comment := args.get("comment"):
            mutation["comment"] = comment

        if ref := args.get("ref"):
            mutation["ref"] = ref

        if "phone_numbers" in args:
            mutation["of_phone_number_ids"] = x2many(
                self=self, model="of.res.partner.phone", input=args.get("phone_numbers")
            )

        if parent := args.get("parent"):
            mutation["parent_id"] = many2one(self=self, model="res.partner", input=parent)

        if title := args.get("title"):
            mutation["title"] = many2one(self=self, model="res.partner.title", input=title)

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
            if select.street:
                odoo_domain += [("street", "ilike", select.street)]
            if select.street2:
                odoo_domain += [("street2", "ilike", select.street2)]
            if select.city:
                odoo_domain += [("city", "ilike", select.city)]
            if select.zip:
                odoo_domain += [("zip", "ilike", select.zip)]
            if select.email:
                odoo_domain += [("email", "ilike", select.email)]

        return odoo_domain
