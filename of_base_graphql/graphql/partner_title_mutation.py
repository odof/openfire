# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .partner_title_type import PartnerTitle


class PartnerTitleCreate(graphene.Mutation):
    _name = "PartnerTitleCreate"

    class Arguments:
        name = graphene.String()
        of_used_for_phone = graphene.Boolean(name="usedForPhone")

    Output = PartnerTitle

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["res.partner.title"]._prepare_mutation_values(**args)
        return env["res.partner.title"].create(values)


class PartnerTitleUpdate(graphene.Mutation):
    _name = "PartnerTitleUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        of_used_for_phone = graphene.Boolean(name="usedForPhone")

    Output = PartnerTitle

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["res.partner.title"]._prepare_mutation_values(**args)
        title = env["res.partner.title"].search([("id", "=", id)])
        title.write(values)
        return title


class PartnerTitleDelete(graphene.Mutation):
    _name = "PartnerTitleDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = PartnerTitle

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "res.partner.title", id)


class PartnerTitleMutation(graphene.ObjectType):
    _name = "PartnerTitleMutation"
    _type = "mutation"

    partner_title_create = PartnerTitleCreate.Field()
    partner_title_update = PartnerTitleUpdate.Field()
    partner_title_delete = PartnerTitleDelete.Field()
