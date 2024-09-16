# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class OFPlanningIntervention(models.Model):
    _inherit = 'calendar.event'

    of_is_customer_sms_sent = fields.Boolean(string="Customer SMS sent ?", default=False)

    def action_send_sms(self):
        return self.env['of.sms'].action_send_sms(self.id, 'calendar.event', self.of_partner_id)

    def _team_reminder_notif_daily(self, reminder_date, tomorrow_date):
        """Team reminder notification daily.

        We send a text message to the teams if the option is enabled.
        Unlike customers, for appointments over several days, we send a reminder text every day.

        Args:
            reminder_date (datetime): The date of the reminder.
            tomorrow_date (datetime): The date of tomorrow.
        """
        intervention_obj = self.env['calendar.event']

        for company in self.env['res.company'].sudo().search([]):
            if company.of_team_alert_intervention_sms:
                for employee in self.env['hr.employee'].with_company(company).search([]):
                    interventions = intervention_obj.search(
                        [
                            ('of_employee_ids', 'in', [employee.id]),
                            ('start', '<=', reminder_date),
                            ('stop', '>=', tomorrow_date),
                            ('of_state', '=', 'confirmed'),
                        ],
                        order='start',
                    )
                    if not interventions:
                        continue

                    message_body = _("Your next interventions :\n")
                    for intervention in interventions:
                        date = fields.Datetime.context_timestamp(
                            intervention, fields.Datetime.from_string(intervention.date)
                        )
                        duration_str = _("duration")
                        message_body += (
                            f"{date.strftime('%d/%M/%Y %H:%M')} "
                            f"({duration_str} {intervention.duration}) : {intervention.name}\n"
                        )
                    employee._message_sms(body=message_body)

    def _customer_reminder_notif_daily(self, reminder_date, tomorrow_date):
        """Customer reminder notification daily.

        We send a text message to the participants if the option is enabled.

        Args:
            end_date_reminder (datetime): The end date of the reminder.
            tomorrow_date (datetime): The date of tomorrow.
        """
        intervention_obj = self.env['calendar.event']
        sms_template = self.env.ref('of_sms.of_sms_planning_customer_appointment_reminder')

        for company in self.env['res.company'].sudo().search([]):
            if company.of_customer_alert_intervention_sms:
                # We retrieve the next day's interventions that have not already been recalled.
                interventions = intervention_obj.search(
                    [
                        ('start', '>=', tomorrow_date),
                        ('start', '<=', reminder_date),
                        ('of_state', '=', 'confirmed'),
                        ('of_is_customer_sms_sent', '=', False),
                    ],
                    order='start',
                )
                for intervention in interventions:
                    intervention._message_sms_with_template(template=sms_template)
                    intervention.of_is_customer_sms_sent = True

    @api.model
    def cron_sms_notif_daily(self):
        """Called by the daily cron job to send the daily SMS reminders."""
        now = fields.datetime.now()
        tomorrow_date = fields.Datetime.context_timestamp(self, now) + timedelta(days=1)
        if now.isoweekday() == 7:  # 7 is Sunday. We don't send reminders on Sunday.
            return True

        if now.isoweekday() == 6:
            # We are on Saturday, we need to send reminders for Monday.
            reminder_date = fields.Datetime.context_timestamp(self, now) + timedelta(days=2)
        else:
            reminder_date = tomorrow_date

        # Get the SMS sender.
        if model := self.env['ir.model'].search([('model', '=', 'calendar.event')], limit=1):
            sender = self.env['of.sms.sender'].search([('model', '=', model)], limit=1)
        else:
            sender = self.env['of.sms.sender'].search([('model', '=', '')], limit=1)

        if not sender:
            _logger.error("This customer has no valid mobile number!")
            return False

        # Send the SMS reminders.
        self._team_reminder_notif_daily(reminder_date, tomorrow_date)
        self._customer_reminder_notif_daily(reminder_date, tomorrow_date)

        return True
