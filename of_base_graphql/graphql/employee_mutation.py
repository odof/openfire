import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .employee_type import Employee


class EmployeeCreate(graphene.Mutation):
    _name = 'EmployeeCreate'

    class Arguments:
        name = graphene.String()
        mobile_phone = graphene.String()
        work_phone = graphene.String()
        work_email = graphene.String()

    Output = Employee

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['hr.employee']._prepare_mutation_values(**args)
        return env['hr.employee'].create(values)


class EmployeeUpdate(graphene.Mutation):
    _name = 'EmployeeUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        mobile_phone = graphene.String()
        work_phone = graphene.String()
        work_email = graphene.String()

    Output = Employee

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['hr.employee']._prepare_mutation_values(**args)
        employee = env['hr.employee'].search([('id', '=', id)])
        return employee.write(values)


class EmployeeDelete(graphene.Mutation):
    _name = 'EmployeeDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = Employee

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'hr.employee', id)


class EmployeeMutation(graphene.ObjectType):
    _name = 'EmployeeMutation'
    _type = 'mutation'

    employee_create = EmployeeCreate.Field()
    employee_update = EmployeeUpdate.Field()
    employee_delete = EmployeeDelete.Field()
