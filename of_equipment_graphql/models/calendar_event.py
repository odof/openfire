# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if "equipments" in args:
            mutation["of_equipment_ids"] = x2many(self=self, model="of.equipment", input=args.get("equipments"))

        # clé en camel case car elle n'est pas directement gérée par graphene
        if "linkedEquipments" in args:
            linked_equipments = args.get("linkedEquipments", [])

            keep = "linkedEquipments" in args.get("keep_relations", {})
            if keep:
                mutation["of_use_equipment"] = len(linked_equipments) > 0
            else:
                mutation["of_use_equipment"] = bool(linked_equipments)

            mutation["of_linked_equipment_ids"] = x2many(
                self=self, model="of.calendar.event.equipment.link", input=linked_equipments, keep=keep
            )
        return mutation
