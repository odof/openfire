# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class Configuration(OdooObjectType):
    _name = 'Configuration'
    _type = 'types'

    mobile_display_planning_days_before = graphene.Int(required=True)
    mobile_display_planning_days_after = graphene.Int(required=True)
    mobile_can_edit_days_before = graphene.Int(required=True)
    mobile_can_edit_days_after = graphene.Int(required=True)
    meeting_timesheet = graphene.String(required=True)
    meeting_timesheet_force = graphene.Boolean(required=True)
    mobile_image_resolution_width = graphene.Int(required=True)
    mobile_image_resolution_height = graphene.Int(required=True)
    mobile_can_create_additional_sale = graphene.Boolean()

    @staticmethod
    def resolve_mobile_display_planning_days_before(root, info):
        env = info.context['env']
        return env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_before')

    @staticmethod
    def resolve_mobile_display_planning_days_after(root, info):
        env = info.context['env']
        return env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_after')

    @staticmethod
    def resolve_mobile_can_edit_days_before(root, info):
        env = info.context['env']
        return env['ir.config_parameter'].sudo().get_param('of_mobile.can_edit_days_before')

    @staticmethod
    def resolve_mobile_can_edit_days_after(root, info):
        env = info.context['env']
        return env['ir.config_parameter'].sudo().get_param('of_mobile.can_edit_days_after')

    @staticmethod
    def resolve_meeting_timesheet(root, info):
        env = info.context['env']
        return env['ir.config_parameter'].sudo().get_param('of_mobile.meeting_timesheet')

    @staticmethod
    def resolve_mobile_image_resolution_width(root, info):
        env = info.context['env']
        return env['ir.config_parameter'].sudo().get_param('of_mobile.image_resolution_width')

    @staticmethod
    def resolve_mobile_image_resolution_height(root, info):
        env = info.context['env']
        return env['ir.config_parameter'].sudo().get_param('of_mobile.image_resolution_height')

    @staticmethod
    def resolve_meeting_timesheet_force(root, info):
        env = info.context['env']
        param = env['ir.config_parameter'].sudo().get_param('of_mobile.meeting_timesheet_force')
        # graphene n'arrive pas à interpréter le true venant des parametres.
        # on le reconverti pour lui
        return bool(param)

    @staticmethod
    def resolve_mobile_can_create_additional_sale(root, info):
        env = info.context['env']
        return env.user.company_id.of_mobile_can_create_additional_sale
