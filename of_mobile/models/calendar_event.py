# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import pytz
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.models import expression

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def _default_of_section_to_display_ids(self):
        section_to_display_ids = self.env["of.planning.intervention.section"].search([])
        return [Command.link(section_to_display.id) for section_to_display in section_to_display_ids]

    of_update_date = fields.Datetime(
        string="Update date",
        help="Most recent update date of every elements in the intervention",
        default=fields.Datetime.now(),
    )

    of_historical_ids = fields.One2many(
        comodel_name="calendar.event",
        compute="_compute_historical_ids",
    )

    of_coming_ids = fields.One2many(
        comodel_name="calendar.event",
        compute="_compute_coming_ids",
    )

    of_section_to_display_ids = fields.Many2many(
        comodel_name="of.planning.intervention.section",
        relation="of_calendar_event_section_rel",
        column1="intervention_id",
        column2="section_id",
        string="Sections to display on the intervention",
        help="By adding or removing a section from this list, you can choose which sections will be displayed on the "
        "mobile app for this intervention.",
        default=lambda r: r._default_of_section_to_display_ids(),
        compute="_compute_of_section_to_display_ids",
        store=True,
        readonly=False,
    )

    of_payment_intervention = fields.Many2one(
        comodel_name="account.payment", string="Intervention Payment", compute="_compute_of_payment"
    )

    of_additional_sale_order_id = fields.Many2one(comodel_name="sale.order", string="Additional Sale")
    of_payment_sale = fields.Many2one(
        comodel_name="account.payment", string="Sale Payment", compute="_compute_of_payment"
    )

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("of_template_id")
    def _compute_of_section_to_display_ids(self):
        for event in self:
            if event.of_template_id:
                event.of_section_to_display_ids = event.of_template_id.section_to_display_ids

    @api.depends("of_partner_id", "of_address_id")
    def _compute_historical_ids(self):
        limit = self.env["ir.config_parameter"].sudo().get_param("of_mobile.history_limit")
        today = fields.Date.today()
        limit_date = today - relativedelta(months=int(limit))
        for event in self:
            event_date = event.start.date()
            if event.of_address_id:
                interventions = event.of_address_id.of_intervention_address_ids
            elif event.of_partner_id:
                interventions = event.of_partner_id.of_intervention_partner_ids
            else:
                event.of_historical_ids = False
                continue

            event.of_historical_ids = interventions.filtered(
                lambda i: self._filterHistoricalIntervention(i.start.date(), event_date, limit_date)
            )

    @api.depends("of_partner_id", "of_address_id")
    def _compute_coming_ids(self):
        for event in self:
            if event.of_address_id:
                interventions = event.of_address_id.of_intervention_address_ids
            elif event.of_partner_id:
                interventions = event.of_partner_id.of_intervention_partner_ids
            else:
                event.of_coming_ids = False
                continue

            event.of_coming_ids = interventions.filtered(
                lambda i: self._filterComingIntervention(i, event.start)
            ).sorted(key=lambda x: x.start)

    def _compute_of_payment(self):
        for event in self:
            payment_intervention = self.env["account.payment"].search([("of_intervention_id", "=", event.id)], limit=1)
            event.of_payment_intervention = payment_intervention.id

            if event.of_additional_sale_order_id:
                payment_sale = self.env["account.payment"].search(
                    [("of_sale_id", "=", event.of_additional_sale_order_id.id)], limit=1
                )
                event.of_payment_sale = payment_sale.id
            else:
                event.of_payment_sale = False

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, list_vals):
        results = super().create(list_vals)
        results._handle_create_events_notifications()
        return results

    def write(self, vals):
        """
        Debrief des changements pour savoir si l'on doit notifier
        On ne notifie que pour les interventions du jour et dans les cas suivants :
            - changement d'intervenant
            - changement d'horaire (pas de notification visible)
            - changement de lieu (pas de notification visible)
            - changement d'état (pas de notification visible)
        Les 3 dernières n'ayant pas de changement de notification visible vont juste être considérées comme des maj
        de l'intervention
        """
        vals["of_update_date"] = fields.Datetime.now()
        defer_push_notification = self._context.get("defer_push_notification")
        new_start_date = vals.get("start")
        is_new_start_date_today = new_start_date and fields.Date.today() == fields.Date.from_string(new_start_date)

        employee_notifications = []
        intervention_updated_notifications = set()

        for event in self:
            if defer_push_notification or (not event._is_intervention_today() and not is_new_start_date_today):
                continue

            if self._has_intervention_changed(event, vals):
                intervention_updated_notifications.add(event)

            if vals.get("of_employee_ids"):
                previous_employee_ids = (
                    {employee.id for employee in event.of_employee_ids} if event.of_employee_ids else set()
                )
                new_employee_ids = set(vals.get("of_employee_ids")[0][2])
                if previous_employee_ids != new_employee_ids:
                    employee_notifications.append((event, previous_employee_ids, new_employee_ids))

        result = super().write(vals)

        if not defer_push_notification:
            self._send_intervention_notifications_on_write(intervention_updated_notifications, employee_notifications)
        return result

    def unlink(self):
        delete_notifications = []

        for event in self:
            employee_ids = event.of_employee_ids.filtered("user_id")
            if event._is_intervention_today():
                delete_notifications.append((event.name, event.start, event.event_tz, employee_ids, event.id))

        result = super().unlink()

        self._handle_delete_events_notifications(delete_notifications)
        return result

    # --------------------------------------------------------------------------
    # Action methods
    # --------------------------------------------------------------------------

    @api.model
    def action_update_date(self, domain_obj):
        of_mobile_days_before = (
            self.env["ir.config_parameter"].sudo().get_param("of_mobile.display_planning_days_before", 0)
        )
        of_mobile_days_after = (
            self.env["ir.config_parameter"].sudo().get_param("of_mobile.display_planning_days_after", 0)
        )

        now = fields.Datetime.now()
        today = fields.Date.today()
        before = today + relativedelta(days=-int(of_mobile_days_before))
        after = today + relativedelta(days=int(of_mobile_days_after))

        domain = [
            ("start", ">=", fields.Date.to_string(before)),
            ("start", "<=", fields.Date.to_string(after)),
            ("of_state", "not in", ["cancel", "postponed"]),
        ]

        domain = expression.AND([domain, domain_obj])

        if interventions := self.env["calendar.event"].sudo().search(domain):
            interventions.write({"of_update_date": now})

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _filterHistoricalIntervention(self, historical_intervention_date, intervention_date, limit_date):
        return intervention_date > historical_intervention_date > limit_date

    def _filterComingIntervention(self, coming_intervention, intervention_date):
        return intervention_date < coming_intervention.start

    def _is_intervention_today(self):
        """
        We consider that an intervention is today if the current date is between the start or end date
        Returns:
            bool: True if the intervention is today, False otherwise
        """
        self.ensure_one()
        today = fields.Date.from_string(fields.Date.today())
        start_date = fields.Date.from_string(self.start)
        end_date = fields.Date.from_string(self.stop)
        return start_date <= today <= end_date

    def _has_intervention_changed(self, intervention, vals):
        """Check if the intervention has its address, start date or state changed

        Args:
            intervention (calendar.event): The intervention to check
            vals (dict): The values to write

        Returns:
            bool: True if the intervention has its address, start date or state changed, False otherwise
        """
        address_id = vals.get("of_address_id", False)
        previous_address_id = intervention.of_address_id.id if intervention.of_address_id else None
        new_start_date = vals.get("start", False)
        state = vals.get("of_state")

        return (
            (address_id and previous_address_id != address_id)
            or (new_start_date and new_start_date != intervention.start)
            or (state and state != intervention.of_state)
        )

    def _send_intervention_notifications_on_write(self, intervention_updated_notifications, employee_notifications):
        """Send notifications to users when an intervention is updated

        Args:
            intervention_updated_notifications (set): Set of interventions that have been updated (address, start date
                or state changed)
            employee_notifications (list): List of tuples containing the intervention, the previous employee_ids and the
                new employee_ids

        Returns:
            None
        """
        employee_obj = self.env["hr.employee"]
        for intervention in intervention_updated_notifications:
            user_ids = intervention.mapped("of_employee_ids.user_id.id")
            for user_id in user_ids:
                notification = {
                    "firebase": {
                        "kind": "data",
                        "user_id": user_id,
                        "payload": {"type": "updated_intervention", "intervention_id": intervention.id},
                    }
                }
                user = self.env["res.users"].browse(user_id)
                user.action_send_notifications(notification)

        for intervention, previous_employee_ids, new_employee_ids in employee_notifications:
            employee_ids = intervention.of_employee_ids
            employee_notify_new_intervention = new_employee_ids - previous_employee_ids
            employee_notify_deleted_intervention = previous_employee_ids - new_employee_ids

            # Si l'intervention est aujourd'hui et que l'on a des utilisateurs à notifier
            if user_ids := [
                employee_id.user_id.id
                for employee_id in employee_ids.filtered(
                    lambda x: x.id in employee_notify_new_intervention and x.user_id
                )
            ]:
                for user_id in user_ids:
                    notification = {
                        "backoffice": {
                            "title": _("New intervention today"),
                            "message": _(
                                "Click <a href='/web#id={}&view_type=form&model={}'>here</a> to open it".format(
                                    intervention.id, "calendar.event"
                                )
                            ),
                            "sticky": False,
                            "warning": True,
                            "message_is_html": True,
                        },
                        "firebase": {
                            "user_id": user_id,
                            "kind": "message_with_data",
                            "title": _("New intervention today"),
                            "message": _("Click here to open it"),
                            "payload": {"type": "new_intervention", "intervention_id": intervention.id},
                        },
                    }
                    user = self.env["res.users"].browse(user_id)
                    user.action_send_notifications(notification)

            tz = pytz.timezone(intervention.event_tz or self.env.context.get("tz"))
            intervention_time = (
                pytz.utc.localize(fields.Datetime.from_string(intervention.start)).astimezone(tz).strftime("%H:%M")
            )

            if employee_ids_to_notify := employee_obj.search(
                [
                    ("id", "in", list(employee_notify_deleted_intervention)),
                    ("user_id", "!=", False),
                ]
            ):
                user_ids = employee_ids_to_notify.mapped("user_id.id")

                for user_id in user_ids:
                    notification = {
                        "backoffice": {
                            "title": _("Operator changement"),
                            "message": _(
                                "You are no more the operator of the intervention {} plannified at {}".format(
                                    intervention.name, intervention_time
                                )
                            ),
                            "sticky": False,
                            "warning": True,
                        },
                        "firebase": {
                            "title": _("Operator changement"),
                            "message": _(
                                "You are no more the operator of the intervention {} plannified at {}".format(
                                    intervention.name, intervention_time
                                )
                            ),
                            "kind": "message_with_data",
                            "user_id": user_id,
                            "payload": {
                                "type": "deleted_intervention",
                                "intervention_id": intervention.id,
                            },
                        },
                    }
                    user = self.env["res.users"].browse(user_id)
                    user.action_send_notifications(notification)

    def _handle_create_events_notifications(self):
        """Send notifications to users when a new intervention is created"""
        defer_push_notification = self._context.get("defer_push_notification", False)
        for event in self:
            if not defer_push_notification and event._is_intervention_today():
                user_ids = event.mapped("of_employee_ids.user_id.id")
                for user_id in user_ids:
                    notification = {
                        "backoffice": {
                            "title": _("New intervention today"),
                            "message": _(
                                "Click <a href='/web#id={}&view_type=form&model={}'>here</a> to open it".format(
                                    event.id, "calendar.event"
                                )
                            ),
                            "sticky": False,
                            "warning": True,
                            "message_is_html": True,
                        },
                        "firebase": {
                            "user_id": user_id,
                            "kind": "message_with_data",
                            "title": _("New intervention today"),
                            "message": _("Click here to open it"),
                            "payload": {"type": "new_intervention", "intervention_id": event.id},
                        },
                    }
                    user = self.env["res.users"].browse(user_id)
                    user.action_send_notifications(notification)

    def _handle_delete_events_notifications(self, delete_notifications):
        """Send notifications to users when an intervention is deleted"""
        for notification in delete_notifications:
            (
                intervention_name,
                intervention_start_date,
                intervention_tz,
                employee_ids,
                intervention_id,
            ) = notification

            tz = pytz.timezone(intervention_tz or self.env.context.get("tz"))
            intervention_time = (
                pytz.utc.localize(fields.Datetime.from_string(intervention_start_date)).astimezone(tz).strftime("%H:%M")
            )

            for user_id in employee_ids.mapped("user_id.id"):
                notification = {
                    "backoffice": {
                        "title": _("Intervention has been deleted"),
                        "message": _(
                            "The intervention {} plannified at {} has been deleted".format(
                                intervention_name, intervention_time
                            )
                        ),
                        "sticky": False,
                        "warning": True,
                    },
                    "firebase": {
                        "title": _("Intervention has been deleted"),
                        "message": _(
                            "The intervention {} plannified at {} has been deleted".format(
                                intervention_name, intervention_time
                            )
                        ),
                        "kind": "message_with_data",
                        "user_id": user_id,
                        "payload": {
                            "type": "deleted_intervention",
                            "intervention_id": intervention_id,
                        },
                    },
                }

                user = self.env["res.users"].browse(user_id)
                user.action_send_notifications(notification)

    def action_mobile_create_invoice(self):
        """
        Create an invoice for the calendar event.
        """
        invoices = self.env["account.move"]
        for event in self:
            if not event.of_fiscal_position_id:
                raise UserError(_("Intervention is non billable, please select a fiscal position."))

            # All lines are linked to order lines so they should be invoiced from the sale order
            if event.of_link_order and not event.of_line_ids.filtered(lambda li: not li.order_line_id):
                raise UserError(
                    _("Invoiceable lines are linked to order lines. Please do the invoicing from the sale order.")
                )

            if event.of_state not in ["confirmed", "ongoing", "done", "unfinished", "postponed"]:
                raise UserError(_("Intervention is non billable because it must be confirmed."))

            # Prepare the invoice data
            invoice_data, messages = event._prepare_invoice()
            if invoice_data:
                move_obj = self.env["account.move"]
                move = move_obj.create(invoice_data)
                move.message_post_with_view(
                    "mail.message_origin_link",
                    values={"self": move, "origin": event},
                    subtype_id=self.env.ref("mail.mt_note").id,
                )
                invoices += move
        return invoices

    # --------------------------------------------------------------------------
    # Graphql methods
    # --------------------------------------------------------------------------

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if additional_sale := args.get("additional_sale"):
            additional_sale["of_is_intervention_order"] = True
            mutation["of_additional_sale_order_id"] = many2one(self=self, model="sale.order", input=additional_sale)

        return mutation
