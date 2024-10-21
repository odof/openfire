# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, fields, models


class OFEquipment(models.Model):
    _inherit = "of.equipment"

    service_request_maintenance_count = fields.Integer(compute="_compute_service_request_count")
    service_request_after_sales_count = fields.Integer(compute="_compute_service_request_count")
    service_request_to_plan_count = fields.Integer(compute="_compute_service_request_count")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    def _compute_service_request_count(self):
        service_request_obj = self.env["of.service.request"]
        maintenance_type = self.env.ref("of_service.of_service_request_type_maintenance")
        after_sales_type = self.env.ref("of_equipment_service.of_service_request_type_after_sales")
        for equipment in self:
            requests = service_request_obj.search([("equipment_ids", "in", equipment.ids)])
            equipment.service_request_maintenance_count = len(
                requests.filtered(lambda r: r.type_id == maintenance_type)
            )
            equipment.service_request_after_sales_count = len(
                requests.filtered(lambda r: r.type_id == after_sales_type)
            )
            equipment.service_request_to_plan_count = len(requests.filtered(lambda r: not r.recurrency))

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_view_service_request_maintenance(self):
        self.ensure_one()
        maintenance_type = self.env.ref("of_service.of_service_request_type_maintenance").id
        return {
            "name": _("Maintenance Service Request"),
            "view_mode": "tree,form",
            "res_model": "of.service.request",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": [("equipment_ids", "in", self.ids), ("type_id", "=", maintenance_type)],
            "context": {
                "default_partner_id": self.customer_id.id,
                "default_address_id": self.site_address_id.id,
                "default_recurrency": True,
                "default_next_date": fields.Date.today(),
                "default_use_equipment": True,
                "default_linked_equipment_ids": self._get_default_equipments_link_values(),
                "default_origin": _("[Equipment] %s") % (self.name or ""),
                "default_type_id": maintenance_type,
            },
        }

    def action_button_view_service_request_after_sales(self):
        after_sales_type = self.env.ref("of_equipment_service.of_service_request_type_after_sales").id
        return {
            "name": _("After-Sales Service Request"),
            "view_mode": "tree,form",
            "res_model": "of.service.request",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": [("equipment_ids", "in", self.ids), ("type_id", "=", after_sales_type)],
            "context": {
                "default_partner_id": self.customer_id.id,
                "default_address_id": self.site_address_id.id,
                "default_recurrency": True,
                "default_next_date": fields.Date.today(),
                "default_use_equipment": True,
                "default_linked_equipment_ids": self._get_default_equipments_link_values(),
                "default_origin": _("[Equipment] %s") % (self.name or ""),
                "default_type_id": after_sales_type,
            },
        }

    def action_button_view_service_request_to_plan(self):
        return {
            "name": _("Service Request To Plan"),
            "view_mode": "tree,form",
            "res_model": "of.service.request",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": [("equipment_ids", "in", self.ids), ("recurrency", "=", False)],
            "context": {
                "default_partner_id": self.customer_id.id,
                "default_address_id": self.site_address_id.id,
                "default_recurrency": False,
                "default_next_date": fields.Date.today(),
                "default_use_equipment": True,
                "default_linked_equipment_ids": self._get_default_equipments_link_values(),
                "default_origin": _("[Equipment] %s") % (self.name or ""),
                "default_type_id": self.env.ref("of_equipment_service.of_service_request_type_after_sales").id,
            },
        }

    def action_button_plan_intervention(self):
        self.ensure_one()
        form_id = self.env.ref("of_service.of_service_request_view_form").id
        return {
            "name": _("Plan an intervention"),
            "view_mode": "form",
            "res_model": "of.service.request",
            "views": [(form_id, "form")],
            "type": "ir.actions.act_window",
            "target": "new",
            "context": {
                "default_partner_id": self.customer_id.id,
                "default_address_id": self.site_address_id.id,
                "default_recurrency": False,
                "default_next_date": fields.Date.today(),
                "default_use_equipment": True,
                "default_linked_equipment_ids": self._get_default_equipments_link_values(),
                "default_origin": _("[Equipment] %s") % (self.name or ""),
                "default_type_id": self.env.ref("of_equipment_service.of_service_request_type_after_sales").id,
            },
        }

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _get_default_equipments_link_values(self):
        """Helper method to get the default values for the linked equipments to the service request/intervention."""
        return [
            Command.create(
                {
                    "equipment_id": equipment.id,
                }
            )
            for equipment in self
        ]
