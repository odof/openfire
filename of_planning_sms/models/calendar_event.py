# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from pytz import timezone

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    of_is_customer_sms_sent = fields.Boolean(string="Customer SMS sent ?", default=False)
    of_customer_sms_number = fields.Char(string="Mobile number", compute='_compute_of_customer_sms_number')

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('of_address_id', 'of_partner_id')
    def _compute_of_customer_sms_number(self):
        for record in self:
            if not (mobile_numbers := record.of_address_id.get_mobile_numbers()):
                mobile_numbers = record.of_partner_id.get_mobile_numbers()
            record.of_customer_sms_number = mobile_numbers and mobile_numbers[0] or False

    # -------------------------------------------------------------------------
    # Actions methods
    # -------------------------------------------------------------------------

    def action_send_sms(self):
        """Send an SMS to the customer. Used in the calendar event form view. (hidden button)"""
        return self.env['of.sms'].action_send_sms(self.id, 'calendar.event', self.of_address_id)

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _sms_get_number_fields(self):
        """Get the fields that contain the customer's mobile number for the SMS."""
        return ['of_customer_sms_number']

    def _sms_get_partner_fields(self):
        """Get the fields that contain the partner for the SMS."""
        fields = super()._sms_get_partner_fields()
        if self.of_type == 'intervention':
            fields = ['of_address_id']
        return fields

    def _sms_get_default_partners(self):
        if self.of_type == 'event':
            # this method is overidden in `calendar_sms` module, and we don't want to call it when the event is
            # an intervention
            return super()._sms_get_default_partners()

        partners = self.env['res.partner']
        for fname in self._sms_get_partner_fields():
            partners = partners.union(*self.mapped(fname))  # ensure ordering
        return partners

    def _team_reminder_notif_daily(self, reminder_start_date, reminder_stop_date):
        """Team reminder notification daily.

        We send a text message to the teams if the option is enabled.
        Unlike customers, for appointments over several days, we send a reminder text every day.

        Args:
            reminder_start_date (datetime): The start date of the reminder (tomorrow, or Monday if today is Saturday).
            reminder_stop_date (datetime): The stop date of the reminder (tomorrow, or Monday if today is Saturday).
        """
        intervention_obj = self.env['calendar.event']

        for company in self.env['res.company'].sudo().search([('of_team_alert_intervention_sms', '=', True)]):
            for employee in self.env['hr.employee'].search([('company_id', '=', company.id)]):
                interventions = intervention_obj.search(
                    [
                        ('of_employee_ids', 'in', [employee.id]),
                        ('start', '>=', reminder_start_date),
                        ('start', '<=', reminder_stop_date),
                        ('of_state', '=', 'confirmed'),
                        ('of_company_id', '=', company.id),
                    ],
                    order='start',
                )
                if not interventions:
                    continue

                message_body = _("Your next interventions :\n")
                for intervention in interventions:
                    date = intervention.start.astimezone(timezone(employee.tz))
                    duration_str = _("duration")
                    message_body += (
                        f"{date.strftime('%d/%m/%Y %H:%M')} "
                        f"({duration_str} {intervention.duration}) : {intervention.name}\n"
                    )
                employee._message_sms(body=message_body)

    def _customer_reminder_notif_daily(self, reminder_start_date, reminder_stop_date):
        """Customer reminder notification daily.

        We send a text message to the participants if the option is enabled.

        Args:
            reminder_start_date (datetime): The start date of the reminder (tomorrow, or Monday if today is Saturday).
            reminder_stop_date (datetime): The stop date of the reminder (tomorrow, or Monday if today is Saturday).
        """
        intervention_obj = self.env['calendar.event']
        sms_template = self.env.ref('of_planning_sms.of_sms_planning_customer_appointment_reminder')

        for company in self.env['res.company'].sudo().search([('of_customer_alert_intervention_sms', '=', True)]):
            # We retrieve the next day's interventions that have not already been recalled.
            interventions = intervention_obj.search(
                [
                    ('start', '>=', reminder_start_date),
                    ('start', '<=', reminder_stop_date),
                    ('of_state', '=', 'confirmed'),
                    ('of_is_customer_sms_sent', '=', False),
                    ('of_company_id', '=', company.id),
                ],
                order='start',
            )
            for intervention in interventions:
                intervention._message_sms_with_template(template=sms_template)
                # intervention.of_is_customer_sms_sent = True

    @api.model
    def cron_sms_daily_event_reminder(self):
        """Called by the daily cron job to send the daily SMS reminders."""
        now = fields.Datetime.now()
        tomorrow_start_date = now.replace(hour=0, minute=0, second=1, microsecond=0) + timedelta(days=1)
        tomorrow_end_date = now.replace(hour=23, minute=59, second=59, microsecond=0) + timedelta(days=1)

        if now.isoweekday() == 7:  # 7 is Sunday. We don't send reminders on Sunday.
            return True

        if now.isoweekday() == 6:
            # We are on Saturday, we need to send reminders for Monday.
            reminder_start_date = now.replace(hour=0, minute=0, second=1, microsecond=0) + timedelta(days=2)
            reminder_stop_date = now.replace(hour=23, minute=59, second=59, microsecond=0) + timedelta(days=2)
        else:
            reminder_start_date = tomorrow_start_date
            reminder_stop_date = tomorrow_end_date

        # Get the SMS sender.
        if model := self.env['ir.model'].search([('model', '=', 'calendar.event')], limit=1):
            sender = self.env['of.sms.sender'].search([('model', '=', model.name)], limit=1)
        else:
            sender = self.env['of.sms.sender'].search([('model', '=', '')], limit=1)

        if not sender:
            _logger.error(f"No SMS sender found for model '{model.name}'.")
            return False

        # Send the SMS reminders.
        self._team_reminder_notif_daily(reminder_start_date, reminder_stop_date)
        self._customer_reminder_notif_daily(reminder_start_date, reminder_stop_date)

        return True
