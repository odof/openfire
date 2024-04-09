import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .employee_type import Employee, EmployeeCreateInput, EmployeeUpdateInput


class EmployeeCreate(graphene.Mutation):
    _name = 'EmployeeCreate'

    class Arguments:
        input = EmployeeCreateInput(required=True)

    Output = Employee

    def mutate(self, info, input):
        env = info.context["env"]

        employee = lazy_create(env, 'hr.employee', input)

        return employee


class EmployeeUpdate(graphene.Mutation):
    _name = 'EmployeeUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = EmployeeUpdateInput(required=True)

    Output = Employee

    def mutate(self, info, id, input):
        env = info.context["env"]

        employee = lazy_update(env, 'hr.employee', id, input)

        return employee


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
