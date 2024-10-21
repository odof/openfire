# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, models

from .tools import _get_values_diff


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("of_no_equipment_auto_creation"):
            self._create_handle_add_equipment_to_vals(vals_list)

        events = super().create(vals_list)

        requests_to_populate = self.env["of.service.request"].browse(
            [
                event.of_request_id.id
                for event, vals in zip(events, vals_list)
                if vals.get("of_use_equipment") and event.of_type == "intervention" and event.of_request_id
            ]
        )
        # Populate service request equipment lines for events created with a service request and equipment
        requests_to_populate and requests_to_populate._populate_service_request_equipment_line()
        return events

    def write(self, vals):
        event_intervention = self.filtered(lambda e: e.of_type == "intervention")
        if "of_request_id" in vals:
            request_by_event = {event: event.of_request_id for event in event_intervention if event.of_request_id}
        if "of_linked_equipment_ids" in vals or "of_use_equipment" in vals:
            saved_equipment_links_by_event = {
                event: {
                    link: {
                        "equipment_id": link.equipment_id.id,
                        "task_id": link.task_id.id,
                        "equipment_report_tmpl_id": link.equipment_report_tmpl_id.id,
                    }
                    for link in event.of_linked_equipment_ids
                }
                for event in event_intervention
                if event.of_linked_equipment_ids
            }
        res = super().write(vals)

        # Handle changes on service request equipment lines
        if "of_request_id" in vals:
            self._handle_service_request_changes(request_by_event, vals)
        if "of_linked_equipment_ids" in vals or "of_use_equipment" in vals:
            self._handle_equipments_change(saved_equipment_links_by_event, vals)
        return res

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_remove_all_equipments(self):
        self.ensure_one()

        request_data = {  # {request_id: {event_id: [{equipment_id, equipment_report_tmpl_id, task_id}]}}
            event.of_request_id: {
                event: [
                    {
                        "equipment_id": link.equipment_id,
                        "equipment_report_tmpl_id": link.equipment_report_tmpl_id,
                        "task_id": link.task_id,
                    }
                    for link in self.of_linked_equipment_ids
                ]
            }
            for event in self
        }
        result = super().action_button_remove_all_equipments()
        self.of_request_id._unlink_service_request_equipment_line(request_data)
        return result

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _prepare_calendar_event_equipment_link_values_from_request_link(self, link, vals=None):
        """Prepare the values to create a new equipment link on a calendar event from an existing service request link.

        Args:
            link (recordset): The service request equipment link to use as a reference.
            vals (dict): The values to write on the calendar event.

        Returns:
            dict: The values to create a new equipment link on the calendar event
        """
        default_values = {
            "equipment_id": link.equipment_id.id,
            "equipment_report_tmpl_id": link.equipment_report_tmpl_id.id,
            "task_id": link.task_id.id,
            "request_link_id": link.id,
        }
        if not vals:
            return default_values

        template = vals.get("of_template_id") and self.env["of.planning.intervention.template"].browse(
            vals["of_template_id"]
        )
        if not default_values["task_id"]:
            default_values["task_id"] = template and template.task_id.id
        if not default_values["equipment_report_tmpl_id"]:
            default_values["equipment_report_tmpl_id"] = template and template.default_equipment_report_tmpl_id.id
        if template.line_ids:
            default_values["line_ids"] = [
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "qty": line.qty,
                        "price_unit": line.price_unit,
                    }
                )
                for line in template.line_ids
            ]
        return default_values

    def _create_handle_add_equipment_to_vals(self, vals_list):
        """Handles the addition of equipment to the values list during event creation."""
        request_obj = self.env["of.service.request"]

        for vals in vals_list:
            if not vals.get("of_use_equipment"):
                continue

            if not (request_id := vals.get("of_request_id")) or not (request := request_obj.browse(request_id)):
                continue

            if vals.get("of_equipment_ids") or vals.get("of_linked_equipment_ids"):
                # Equipment is already provided, skip further processing
                continue

            # No equipment provided; fetch all from the service request
            vals["of_linked_equipment_ids"] = [
                Command.create(self._prepare_calendar_event_equipment_link_values_from_request_link(link, vals))
                for link in request.linked_equipment_ids
            ]

    def _handle_service_request_changes(self, request_by_event, vals):
        """Handle changes to the service request."""
        if "of_request_id" in vals:
            if not vals["of_request_id"]:
                self._handle_service_request_empty_request(request_by_event)
            else:
                self._handle_service_request_add_missing_equipment()
                self._handle_service_request_switch_request(request_by_event)

    def _handle_service_request_empty_request(self, request_by_event):
        """
        Handles the removal of service requests from calendar events.

        This method filters the events that have had their service requests removed and ensures that the corresponding
        equipment lines are also removed.

        Args:
            request_by_event (dict): A dictionary mapping events to their associated service requests.
        """
        events_with_request = self.filtered(lambda e: e in request_by_event and not e.of_request_id)
        requests_to_remove = self.env["of.service.request"].browse(
            [request_by_event[event].id for event in events_with_request]
        )
        requests_to_remove._unlink_service_request_equipment_line()

    def _handle_service_request_switch_request(self, request_by_event):
        """
        Handles the switching of service requests for calendar events.

        This method performs the following actions:
        1. Identifies events where the service request has been modified and removes the equipment lines from the
            previously linked service request.
        2. Identifies events where a new service request has been set or the service request has been changed, and adds
            the equipment lines to the new linked service request.

        Args:
            request_by_event (dict): A dictionary mapping events to their corresponding service requests.
        """
        events_with_modified_request = self.filtered(
            lambda e: e in request_by_event and e.of_request_id != request_by_event[e]
        )
        requests_to_remove = self.env["of.service.request"].browse(
            [request_by_event[event].id for event in events_with_modified_request]
        )
        requests_to_remove._unlink_service_request_equipment_line()

        events_with_new_request = self.filtered(
            lambda e: e not in request_by_event or e.of_request_id != request_by_event[e]
        )
        events_with_new_request.mapped("of_request_id")._populate_service_request_equipment_line()

    def _handle_service_request_add_missing_equipment(self):
        """Add missing equipment link to the linked service request.
        As we are linking the event to a service request, we need to ensure that all equipment links are present on the
        service request too.
        """
        for event in self.filtered(lambda e: e.of_request_id and e.of_use_equipment):
            if missing_links := [
                link
                for link in event.of_linked_equipment_ids
                if not event.of_request_id.linked_equipment_ids.filtered(
                    lambda lnk: lnk.equipment_id == link.equipment_id and lnk.task_id == link.task_id
                )
            ]:
                event.of_request_id.write(
                    {
                        "linked_equipment_ids": [
                            Command.create(self._prepare_calendar_event_equipment_link_values_from_request_link(link))
                            for link in missing_links
                        ]
                    }
                )
                # we need to recompute duration on the service request as it can be impacted by the added equipment
                event.of_request_id._compute_duration()
                # Log a message on the service request to inform the user that equipment has been added
                request_message = _(
                    "One or more items of equipment have been added to this SR from the event %(event)s: "
                    "%(equipments)s",
                    event=event._get_html_link(),
                    equipments=", ".join(link.equipment_id.name for link in missing_links),
                )
                event.of_request_id.message_post(body=request_message)

    def _handle_equipments_change(self, saved_equipment_links_by_event, vals):
        """Apply changes on service request equipment lines when equipments of an event are modified.

        Adds, updates, or removes equipment lines from the service requests based on the changes made to the equipment
        links on the events.

        Args:
            saved_equipment_links_by_event (dict): dictionary of events and their related equipment links before the
                changes {event: {link: {equipment_id, task_id, equipment_report_tmpl_id}}}
            vals (dict): dictionary of values to write on the events
        """

        links_action = {"added": [], "removed": [], "updated": []}
        for event, equipment_links_data in saved_equipment_links_by_event.items():
            for link in event.of_linked_equipment_ids:
                if link not in equipment_links_data:
                    links_action["added"].append(link)
                elif (
                    link.equipment_id.id != equipment_links_data[link]["equipment_id"]
                    or link.task_id.id != equipment_links_data[link]["task_id"]
                    or link.equipment_report_tmpl_id.id != equipment_links_data[link]["equipment_report_tmpl_id"]
                ):
                    links_action["updated"].append({"link": link, "old_values": equipment_links_data[link]})
            for link in equipment_links_data:
                if link.id not in event.of_linked_equipment_ids.ids:
                    links_action["removed"].append(link)

        if "of_use_equipment" in vals and not vals["of_use_equipment"]:
            # Events for which has been removed all equipments, we need to remove the equipment lines from
            # linked service request
            events_with_request = self.filtered(
                lambda e: e in saved_equipment_links_by_event and not e.of_use_equipment
            )
            events_with_request.mapped("of_request_id")._unlink_service_request_equipment_line()

        if links_action["removed"]:
            self._handle_equipment_changes_removed_links(saved_equipment_links_by_event)

        if links_action["updated"]:
            self._handle_equipment_changes_updated_links(saved_equipment_links_by_event, links_action["updated"])

        if links_action["added"]:
            self._handle_equipment_changes_added_links(saved_equipment_links_by_event, links_action["added"])

    def _sync_service_request_equipment_links(self, added_links=None, updated_links=None, removed_links=None):
        """
        Synchronizes service request equipment links based on the provided added, updated, and removed event equipment
        links.

        Args:
            added_links (list, optional): List of records (`of.calendar.event.equipment.link`) to add to the service
                request.
            updated_links (list, optional): List of updated equipment links on the events.
                This list should contain dictionaries with the following keys:
                    - link (recordset): The updated equipment link `of.calendar.event.equipment.link`
                    - old_values (dict): The old values of the equipment link.
            removed_links (list, optional): List of records (`of.calendar.event.equipment.link`) to remove from the
                service request.

        Returns:
            None
        """

        if not (added_links or updated_links or removed_links):
            return

        if added_links:
            for event_equipment_lnk in added_links:  # [link, ...]
                if service_request := event_equipment_lnk.event_id.of_request_id:
                    request_equipment_lnk_vals = event_equipment_lnk._prepare_service_request_equipment_link_values()
                    request_equipment_lnk_vals["service_request_id"] = service_request.id
                    event_equipment_lnk.request_link_id = (
                        self.env["of.service.request.equipment.link"].create(request_equipment_lnk_vals).id
                    )
                    event_equipment_lnk._request_post_new_equipment_added_message()
        if updated_links:
            for data in updated_links:  # [{"link": link, "old_values": old_values}, ...]
                event_equipment_lnk = data["link"]
                if (service_request := event_equipment_lnk.event_id.of_request_id) and (
                    request_equipment_lnk := service_request.mapped("linked_equipment_ids").filtered(
                        lambda request_lnk: request_lnk.id == event_equipment_lnk.request_link_id.id
                    )
                ):
                    # Write the diff on the service request equipment link
                    new_values = _get_values_diff(
                        data["old_values"], event_equipment_lnk._prepare_service_request_equipment_link_values()
                    )
                    request_equipment_lnk.write(new_values)
                    # Post a message on the event and the service request to inform about the change
                    event_equipment_lnk._post_self_update_message(data["old_values"], new_values)
                    request_equipment_lnk._post_request_message(
                        event_equipment_lnk.event_id, data["old_values"], new_values
                    )

        if removed_links:
            for event_equipment_lnk in removed_links:  # [link, ...]
                if service_request := event_equipment_lnk.event_id.of_request_id:
                    service_request.mapped("linked_equipment_ids").filtered(
                        lambda request_lnk: request_lnk.id == event_equipment_lnk.request_link_id.id
                    ).unlink()

    def _handle_equipment_changes_removed_links(self, saved_equipment_links_by_event):
        """Removes the equipment lines from the service requests when equipment links have been removed from the events.

        Args:
            saved_equipment_links_by_event (dict): A dictionary where keys are events and values are dictionaries
                mapping equipment IDs to their respective links. (e.g {event: {link.id: link.equipment_id.id}})
        """
        events_with_modified_equipments = self.filtered(
            lambda e: e in saved_equipment_links_by_event
            and e.of_linked_equipment_ids.ids != saved_equipment_links_by_event[e].keys()
        )
        request_data = {  # {request_id: {event_id: [equipment_ids]}}
            event.of_request_id: {event: list(saved_equipment_links_by_event[event].values())}
            for event in events_with_modified_equipments
        }
        events_with_modified_equipments.mapped("of_request_id")._unlink_service_request_equipment_line(request_data)

    def _handle_equipment_changes_updated_links(self, saved_equipment_links_by_event, updated_links):
        """Updates the equipment lines in the service requests when equipment links have been modified on the events.
        This method performs the following actions:
            * Update the equipment link lines on the service request.
                As we updated equipment links on the event, we need to ensure that the corresponding equipment link
                lines are updated on the linked service request.
            * Update the service request equipment lines for the events that have modified equipment links.

        Args:
            saved_equipment_links_by_event (dict): A dictionary where the keys are events and the values are
                dictionaries mapping link IDs to old equipment IDs. (e.g {event: {link.id: link.equipment_id.id}})
        """

        self._sync_service_request_equipment_links(updated_links=updated_links)

        # Get events with modified equipment links by diffing the equipment IDs of the event with the saved equipment
        if events_with_modified_equipments := self.filtered(lambda e: e in saved_equipment_links_by_event):
            # Build dictionary of data used to check if the equipment lines need to be updated
            request_data = {  # {request_id: {event_id: {link_id: {old_equipment_id, new_equipment_id}}}}
                event.of_request_id: {
                    event: {
                        link.id: {
                            "old_equipment_id": link_values["equipment_id"],
                            "new_equipment_id": event.of_linked_equipment_ids.filtered(
                                lambda line: line.id == link.id
                            ).equipment_id.id,
                        }
                        for link, link_values in saved_equipment_links_by_event[event].items()
                    }
                }
                for event in events_with_modified_equipments
            }
            events_with_modified_equipments.mapped("of_request_id")._update_service_request_equipment_line(request_data)

    def _handle_equipment_changes_added_links(self, saved_equipment_links_by_event, added_links):
        """
        Handles the addition of new equipment links to calendar events, and updates the corresponding service requests.
        This method performs the following actions:

        * Create the new equipment link lines on the service request.
            As we added new equipment links to the event, we need to ensure that the corresponding equipment link
            lines exist on the linked service request.
        * Populate the service request equipment lines for the events that have new equipment links
            As we added new equipment links to the event, we need to ensure that the corresponding equipment lines are
            created on the linked service

        Args:
            saved_equipment_links_by_event (dict): A dictionary where keys are events and values are dictionaries
                mapping equipment IDs to their respective details.

        Returns:
            None
        """
        self._sync_service_request_equipment_links(added_links=added_links)

        events_with_new_equipments = self.filtered(
            lambda e: e not in saved_equipment_links_by_event
            or e.of_linked_equipment_ids.ids != list(saved_equipment_links_by_event[e].keys())
        )
        events_with_new_equipments.mapped("of_request_id")._populate_service_request_equipment_line()
