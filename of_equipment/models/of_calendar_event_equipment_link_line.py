# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class OFCalendarEventEquipmentLinkLine(models.Model):
    _name = "of.calendar.event.equipment.link.line"
    _inherit = "of.planning.intervention.line.mixin"
    _description = "Invoicing line for equipment linked to a calendar event"

    link_id = fields.Many2one(
        comodel_name="of.calendar.event.equipment.link", string="Equipment link", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="link_id.event_id.of_company_id")
    partner_id = fields.Many2one(related="link_id.event_id.of_partner_id")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("link_id")
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.link_id.event_id.of_currency_id

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("of_equipment_line_no_sync"):
            self._sync_intervention_line(zip(lines, vals_list))
        return lines

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("of_equipment_line_no_sync") and any(
            field in vals for field in self._get_field_names_to_sync()
        ):
            self._sync_intervention_line([(line, vals) for line in self])
        return res

    def unlink(self):
        if not self.env.context.get("of_equipment_line_no_sync"):
            intervention_lines = self.mapped("link_id.event_id.of_line_ids").filtered(
                lambda el: el.equipment_link_line_id in self
            )
            self._post_event_message("delete")
        res = super().unlink()
        if not self.env.context.get("of_equipment_line_no_sync"):
            self._delete_intervention_lines(intervention_lines)
        return res

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _get_fiscal_position_taxes(self):
        """
        Get the fiscal position to use for taxes computation.
        See `of.planning.intervention.line.mixin._get_fiscal_position_taxes()`.
        """
        self.ensure_one()
        return self.link_id.event_id.of_fiscal_position_id

    def _sync_intervention_line(self, data=None):
        """
        Synchronize the intervention line with the equipment link line.
        This method is called when creating or updating equipment link lines to update or create the corresponding
        intervention lines.

        Args:
            data (list): List of tuples (equipment_link_line, equipment_link_line_vals).
        """
        if not data:
            return

        # group by events
        data_by_event = {}
        for line, vals in data:
            data_by_event.setdefault(line.link_id.event_id, []).append((line, vals))

        for event, lines_data in data_by_event.items():
            # split lines to update and create
            to_update, to_create = [], []
            event_intervention_lines = event.of_line_ids.filtered(lambda el: el.intervention_id == event)
            equipment_link_lines = event_intervention_lines.mapped("equipment_link_line_id")
            for link_line, vals in lines_data:
                if link_line in equipment_link_lines:
                    to_update.append((link_line, vals))
                else:
                    to_create.append((link_line, vals))

            # update existing lines
            proceeded_lines = self.env["of.planning.intervention.line"].browse()
            for link_line, vals in to_update:
                intervention_line = event_intervention_lines.filtered(lambda el: el.equipment_link_line_id == link_line)
                values = self._build_intervention_line_values(event, link_line, vals, mode="update")
                post_data = {}
                if "product_id" in vals:
                    post_data["product"] = intervention_line.name
                intervention_line.with_context(of_equipment_line_no_sync=True).write(values)
                link_line._post_event_message(mode="update", data=post_data)
                proceeded_lines += intervention_line

            # create new lines
            link_lines = self.env["of.calendar.event.equipment.link.line"].browse(
                [link_line.id for link_line, _dummy in to_create]
            )
            vals_list = [
                self._build_intervention_line_values(event, link_line, vals, mode="create")
                for link_line, vals in to_create
            ]
            new_lines = self.env["of.planning.intervention.line"].create(vals_list)
            link_lines._post_event_message(mode="create")
            proceeded_lines += new_lines

        # recompute amounts
        if proceeded_lines:
            proceeded_lines._compute_amount()
            proceeded_lines.mapped("intervention_id")._compute_amount()

    def _get_field_names_to_sync(self):
        return (
            "product_id",
            "uom_id",
            "qty",
            "price_unit",
            "tax_ids",
            "name",
        )

    def _build_intervention_line_values(self, event, link_line, vals, mode="update"):
        """
        Build the values to update the intervention line from the equipment link line values.

        Args:
            event (Recordset): Calendar event.
            link_line (Recordset): Equipment link line.
            vals (dict): Equipment link line values.

        Returns:
            dict: Values to update the intervention line.
        """
        if mode not in ("create", "update"):
            return {}
        if mode == "create":
            return {
                "equipment_link_line_id": link_line.id,
                "product_id": vals.get("product_id"),
                "uom_id": vals.get("uom_id"),
                "qty": vals.get("qty"),
                "price_unit": vals.get("price_unit"),
                "tax_ids": vals.get("tax_ids"),
                "name": vals.get("name"),
                "intervention_id": event.id,
            }

        return {field: vals[field] for field in self._get_field_names_to_sync() if field in vals}

    def _delete_intervention_lines(self, intervention_lines=None):
        """
        Delete the given intervention lines and recompute the amounts of the corresponding interventions.

        Args:
            intervention_lines (Recordset): Intervention lines to delete.
        """
        if intervention_lines:
            events = intervention_lines.mapped("intervention_id")
            intervention_lines.unlink()
            events._compute_amount()

    def _post_event_message(self, mode="create", data=None):
        """
        Post a message on the linked event to inform that a new equipment link line has been created, updated or
        deleted.

        Args:
            mode (str): Mode of the operation ("create", "update", "delete").
            data (dict): Additional data to display in the message.
        """
        if mode not in ("create", "update", "delete"):
            return
        if data is None:
            data = {}
        for line in self:
            if mode == "create":
                message = _(
                    "A new invoicing line has been created from equipment %(eq_name)s: %(name)s",
                    eq_name=line.link_id.equipment_id.name,
                    name=line.name,
                )
            elif mode == "update":
                product_switch = False
                if product := data.get("product"):
                    product_switch = _("(Old: %(from_product)s)", from_product=product)
                message = _(
                    "An invoicing line has been updated from equipment %(eq_name)s: %(name)s%(product_switch)s",
                    eq_name=line.link_id.equipment_id.name,
                    name=line.name,
                    product_switch=f"<br>{product_switch}" if product_switch else "",
                )
            else:
                message = _(
                    "An invoicing line has been deleted from equipment %(eq_name)s: %(name)s",
                    eq_name=line.link_id.equipment_id.name,
                    name=line.name,
                )
            line.link_id.event_id.message_post(body=message)
