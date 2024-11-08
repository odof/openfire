# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .equipment_intervention_report_template_type import (
    EquipmentInterventionReportTemplate,
    EquipmentInterventionReportTemplateFilterInput,
)


class EquipmentInterventionReportTemplateQuery(graphene.ObjectType):
    _name = "EquipmentInterventionReportTemplateQuery"
    _type = "query"

    equipmentInterventionReportTemplates = graphene.List(
        graphene.NonNull(EquipmentInterventionReportTemplate),
        select=graphene.Argument(EquipmentInterventionReportTemplateFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_equipmentInterventionReportTemplates(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["of.equipment.intervention.report.template"]._prepare_graphql_domain(
            select=select, domain=domain
        )

        return env["of.equipment.intervention.report.template"].search(odoo_domain, offset=offset, limit=limit)
