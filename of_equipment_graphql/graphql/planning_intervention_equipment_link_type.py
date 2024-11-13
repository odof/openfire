# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.image_type import Image, ImageInput
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput
from odoo.addons.of_planning_graphql.graphql.planning_intervention_task_type import (
    PlanningInterventionTask,
    PlanningInterventionTaskInput,
)

from .equipment_intervention_report_template_type import (
    EquipmentInterventionReportTemplate,
    EquipmentInterventionReportTemplateInput,
)
from .equipment_type import Equipment, EquipmentInput


class PlanningInterventionEquipmentLink(OdooObjectType):
    _name = "PlanningInterventionEquipmentLink"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    partner = graphene.Field(Partner)
    site_address = graphene.Field(Partner)
    address = graphene.Field(Partner)
    equipment_id = graphene.Field(Equipment, name="equipment", required=True)
    task = graphene.Field(PlanningInterventionTask)
    equipment_report_template = graphene.Field(EquipmentInterventionReportTemplate)
    images = graphene.NonNull(graphene.List(graphene.NonNull(Image)))
    report_text = graphene.String()

    @staticmethod
    def resolve_task(root, info):
        return root.task_id or None

    @staticmethod
    def resolve_equipment_report_template(root, info):
        return root.equipment_report_tmpl_id or None

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None

    @staticmethod
    def resolve_address(root, info):
        return root.address_id or None

    @staticmethod
    def resolve_site_address(root, info):
        return root.site_address_id or None

    @staticmethod
    def resolve_images(root, info):
        return root.all_image_ids or []


class PlanningInterventionEquipmentLinkInput(graphene.InputObjectType):
    _name = "PlanningInterventionEquipmentLinkInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    partner = graphene.Field(PartnerInput)
    site_address = graphene.Field(PartnerInput)
    address = graphene.Field(PartnerInput)
    equipment = graphene.Field(EquipmentInput)
    task = graphene.Field(PlanningInterventionTaskInput)
    equipment_report_template = graphene.Field(EquipmentInterventionReportTemplateInput)
    images = graphene.List(graphene.NonNull(ImageInput))
    report_text = graphene.String()


class PlanningInterventionEquipmentLinkFilterInput(PlanningInterventionEquipmentLinkInput):
    _name = "PlanningInterventionEquipmentLinkFilterInput"
