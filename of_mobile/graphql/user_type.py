# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .fcm_token_type import FCMToken, FCMTokenInput


class User(OdooObjectType):
    _name = 'User'
    _type = 'types'

    interventions_access_right = graphene.String(required=True)
    sales_access_right = graphene.String(required=True)
    account_access_right = graphene.String(required=True)
    partner_manager_access_right = graphene.String(required=True)
    price_change_access_right = graphene.String(required=True)
    of_fcm_token_ids = graphene.List(graphene.NonNull(FCMToken), name='FCMTokens')

    @staticmethod
    def resolve_interventions_access_right(root, info):
        if root.has_group('of_planning.group_planning_intervention_manager'):
            return 'manager'
        elif root.has_group('of_planning.group_planning_intervention_responsible'):
            return 'responsible'
        elif root.has_group('of_planning.group_planning_intervention_read_all_write_own'):
            return 'modification'
        else:
            return 'access'

    @staticmethod
    def resolve_sales_access_right(root, info):
        if root.has_group('sales_team.group_sale_manager'):
            return 'manager'
        elif root.has_group('of_access_control.of_group_sale_responsible'):
            return 'responsible'
        elif root.has_group('sales_team.group_sale_salesman_all_leads'):
            return 'salesman_all_leads'
        elif root.has_group('sales_team.group_sale_salesman'):
            return 'salesman'
        else:
            return 'none'

    @staticmethod
    def resolve_account_access_right(root, info):
        if root.has_group('account.group_account_manager'):
            return 'adviser'
        elif root.has_group('account.group_account_user'):
            return 'accountant'
        elif root.has_group('account.group_account_invoice'):
            return 'billing'
        else:
            return 'none'

    @staticmethod
    def resolve_partner_manager_access_right(root, info):
        return 'manager' if root.has_group('base.group_partner_manager') else 'none'

    @staticmethod
    def resolve_price_change_access_right(root, info):
        return 'allowed' if root.has_group('of_sale.group_price_change') else 'none'


class UserInput(graphene.InputObjectType):
    _name = 'UserInput'
    _type = 'types'

    fcm_tokens = graphene.List(graphene.NonNull(FCMTokenInput))
