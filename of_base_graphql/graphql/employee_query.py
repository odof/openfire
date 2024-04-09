import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .employee_type import Employee, EmployeeFilterInput


class EmployeeQuery(graphene.ObjectType):
    _name = 'EmployeeQuery'
    _type = 'query'

    employees = graphene.List(
        graphene.NonNull(Employee),
        filter=graphene.Argument(EmployeeFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_employees(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
            'company_id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.mobile_phone:
                odoo_domain += [('mobile_phone', 'ilike', filter.mobile_phone)]
            if filter.work_phone:
                odoo_domain += [('work_phone', 'ilike', filter.work_phone)]
            if filter.work_email:
                odoo_domain += [('work_email', 'ilike', filter.work_email)]
            if filter.company_id:
                odoo_domain += [('company_id', '=', filter.company_id)]

        return env['hr.employee'].search(odoo_domain, offset=offset, limit=limit)
