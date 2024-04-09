# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.company_type import Company


class CompanyCreate(graphene.Mutation):
    _name = 'CompanyCreate'

    class Arguments:
        name = graphene.String()

    Output = Company

    def mutate(self, info, **args):
        env = info.context['env']
        values = env['res.company']._prepare_mutation_values(**args)
        return env['res.company'].create(values)


class CompanyUpdate(graphene.Mutation):
    _name = 'CompanyUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()

    Output = Company

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['res.company']._prepare_mutation_values(**args)
        company = env['res.company'].search([('id', '=', id)])
        company.write(values)
        return company


class CompanyMutation(graphene.ObjectType):
    _name = 'CompanyMutation'
    _type = 'mutation'

    company_create = CompanyCreate.Field()
    company_update = CompanyUpdate.Field()
