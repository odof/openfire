# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import pytz
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.models import expression


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def _default_of_section_to_display_ids(self):
        section_to_display_ids = self.env['of.planning.intervention.section'].search([])
        return [Command.link(section_to_display.id) for section_to_display in section_to_display_ids]

    of_update_date = fields.Datetime(
        string='Update date',
        help="Most recent update date of every elements in the intervention",
        default=fields.Datetime.now(),
    )

    of_historical_ids = fields.One2many(
        comodel_name='calendar.event',
        compute="_compute_historical_ids",
    )

    of_coming_ids = fields.One2many(
        comodel_name='calendar.event',
        compute="_compute_coming_ids",
    )

    of_section_to_display_ids = fields.Many2many(
        comodel_name='of.planning.intervention.section',
        relation='of_calendar_event_section_rel',
        column1='intervention_id',
        column2='section_id',
        string="Sections to display on the intervention",
        help="By adding or removing a section from this list, you can choose which sections will be displayed on the "
        "mobile app for this intervention.",
        default=lambda r: r._default_of_section_to_display_ids(),
        compute='_compute_of_section_to_display_ids',
        store=True,
        readonly=False,
    )

    of_mobile_report_send_date = fields.Datetime(string="Send date report from Mobile")
    of_payment_intervention = fields.Many2one(
        comodel_name='account.payment', string="Payment", compute='_compute_of_payment'
    )

    @api.depends('of_template_id')
    def _compute_of_section_to_display_ids(self):
        for event in self:
            if event.of_template_id:
                event.of_section_to_display_ids = event.of_template_id.section_to_display_ids

    def _compute_of_payment(self):
        for event in self:
            payment = self.env['account.payment'].search([('intervention_id', '=', event.id)], limit=1)
            event.of_payment_intervention = payment.id

    @api.model_create_multi
    def create(self, list_vals):
        defer_push_notification = self._context.get('defer_push_notification', False)

        results = super().create(list_vals)
        for result in results:
            if not defer_push_notification and self._is_intervention_today(result):
                user_ids = result.mapped('of_employee_ids.user_id.id')
                for user_id in user_ids:
                    notification = {
                        'backoffice': {
                            'title': _("New intervention today"),
                            'message': _(
                                "Click <a href='/web#id={}&view_type=form&model={}'>here</a> to open it".format(
                                    result.id, 'calendar.event'
                                )
                            ),
                            'sticky': False,
                            'warning': True,
                            'message_is_html': True,
                        },
                        'firebase': {
                            'user_id': user_id,
                            'kind': 'message_with_data',
                            'title': _("New intervention today"),
                            'message': _('Click here to open it'),
                            'payload': {'type': 'new_intervention', 'intervention_id': result.id},
                        },
                    }
                    user = self.env['res.users'].browse(user_id)
                    user.send_notif(notification)

        return results

    def write(self, vals):
        vals['of_update_date'] = fields.Datetime.now()

        # Debrief des changements pour savoir si l'on doit notifier
        # On ne notifie que pour les interventions du jour et dans les cas suivants :
        # - changement d'intervenant
        # - changement d'horaire (pas de notification visible)
        # - changement de lieu (pas de notification visible)
        # - changement d'état (pas de notification visible)
        # Les 3 dernières n'ayant pas de changement de notification visible vont
        # juste être considérées comme des maj de l'intervention
        employee_notifications = []
        intervention_updated_notifications = set()

        defer_push_notification = self._context.get('defer_push_notification', False)

        new_start_date = vals.get('start', False)
        is_new_start_date_today = False

        if new_start_date:
            today = fields.Date.from_string(fields.Date.today())
            new_start_date_parsed = fields.Date.from_string(new_start_date)
            is_new_start_date_today = today == new_start_date_parsed

        for intervention in self:
            if defer_push_notification:
                continue

            if not self._is_intervention_today(intervention) and not is_new_start_date_today:
                continue

            address_id = vals.get('of_address_id', False)

            previous_address_id = intervention.of_address_id.id if intervention.of_address_id else None
            if address_id and previous_address_id != address_id:
                intervention_updated_notifications.add(intervention)

            if new_start_date and new_start_date != intervention.start:
                intervention_updated_notifications.add(intervention)

            state = vals.get('of_state')
            if state and state != intervention.of_state:
                intervention_updated_notifications.add(intervention)

            if vals.get('employee_ids'):
                previous_employee_ids = (
                    set([employee.id for employee in intervention.of_employee_ids])
                    if intervention.of_employee_ids
                    else set()
                )
                new_employee_ids = set(vals.get('of_employee_ids')[0][2])

                if previous_employee_ids != new_employee_ids:
                    employee_notifications.append((intervention, previous_employee_ids, new_employee_ids))

        result = super().write(vals)

        if not defer_push_notification:
            employee_obj = self.env['hr.employee']
            for intervention in intervention_updated_notifications:
                user_ids = intervention.mapped('of_employee_ids.user_id.id')
                for user_id in user_ids:
                    notification = {
                        'firebase': {
                            'kind': 'data',
                            'user_id': user_id,
                            'payload': {'type': 'updated_intervention', 'intervention_id': intervention.id},
                        }
                    }
                    user = self.env['res.users'].browse(user_id)
                    user.send_notif(notification)

            for employee_notification in employee_notifications:
                intervention, previous_employee_ids, new_employee_ids = employee_notification

                employee_ids = intervention.of_employee_ids

                employee_notify_new_intervention = new_employee_ids - previous_employee_ids
                employee_notify_deleted_intervention = previous_employee_ids - new_employee_ids

                user_ids = [
                    employee_id.user_id.id
                    for employee_id in employee_ids.filtered(
                        lambda x: x.id in employee_notify_new_intervention and x.user_id
                    )
                ]

                # Si l'intervention est aujourd'hui et que l'on a des utilisateurs à notifier
                if user_ids:
                    for user_id in user_ids:
                        notification = {
                            'backoffice': {
                                'title': _("New intervention today"),
                                'message': _(
                                    "Click <a href='/web#id={}&view_type=form&model={}'>here</a> to open it".format(
                                        intervention.id, 'calendar.event'
                                    )
                                ),
                                'sticky': False,
                                'warning': True,
                                'message_is_html': True,
                            },
                            'firebase': {
                                'user_id': user_id,
                                'kind': 'message_with_data',
                                'title': _("New intervention today"),
                                'message': _('Click here to open it'),
                                'payload': {'type': 'new_intervention', 'intervention_id': intervention.id},
                            },
                        }
                        user = self.env['res.users'].browse(user_id)
                        user.send_notif(notification)

                tz = pytz.timezone(intervention.event_tz or self.env.context.get('tz'))

                employee_ids_to_notify = employee_obj.search(
                    [
                        ('id', 'in', list(employee_notify_deleted_intervention)),
                        ('user_id', '!=', False),
                    ]
                )

                intervention_time = (
                    pytz.utc.localize(fields.Datetime.from_string(intervention.start)).astimezone(tz).strftime('%H:%M')
                )

                if employee_ids_to_notify:
                    user_ids = employee_ids_to_notify.mapped('user_id.id')

                    for user_id in user_ids:
                        notification = {
                            'backoffice': {
                                'title': _("Operator changement"),
                                'message': _(
                                    "You are no more the operator of the intervention {} plannified at {}".format(
                                        intervention.name, intervention_time
                                    )
                                ),
                                'sticky': False,
                                'warning': True,
                            },
                            'firebase': {
                                'title': _("Operator changement"),
                                'message': _(
                                    "You are no more the operator of the intervention {} plannified at {}".format(
                                        intervention.name, intervention_time
                                    )
                                ),
                                'kind': 'message_with_data',
                                'user_id': user_id,
                                'payload': {
                                    'type': 'deleted_intervention',
                                    'intervention_id': intervention.id,
                                },
                            },
                        }
                        user = self.env['res.users'].browse(user_id)
                        user.send_notif(notification)

        return result

    def unlink(self):
        delete_notifications = []

        for intervention in self:
            employee_ids = intervention.of_employee_ids.filtered('user_id')
            if self._is_intervention_today(intervention):
                delete_notifications.append(
                    (intervention.name, intervention.start, intervention.event_tz, employee_ids, intervention.id)
                )

        result = super().unlink()

        for notification in delete_notifications:
            (
                intervention_name,
                intervention_start_date,
                intervention_tz,
                employee_ids,
                intervention_id,
            ) = notification

            tz = pytz.timezone(intervention_tz or self.env.context.get('tz'))

            intervention_time = (
                pytz.utc.localize(fields.Datetime.from_string(intervention_start_date)).astimezone(tz).strftime('%H:%M')
            )

            user_ids = employee_ids.mapped('user_id.id')

            for user_id in user_ids:
                notification = {
                    'backoffice': {
                        'title': _("Intervention has been deleted"),
                        'message': _(
                            "The intervention {} plannified at {} has been deleted".format(
                                intervention_name, intervention_time
                            )
                        ),
                        'sticky': False,
                        'warning': True,
                    },
                    'firebase': {
                        'title': _("Intervention has been deleted"),
                        'message': _(
                            "The intervention {} plannified at {} has been deleted".format(
                                intervention_name, intervention_time
                            )
                        ),
                        'kind': 'message_with_data',
                        'user_id': user_id,
                        'payload': {
                            'type': 'deleted_intervention',
                            'intervention_id': intervention_id,
                        },
                    },
                }

                user = self.env['res.users'].browse(user_id)
                user.send_notif(notification)

        return result

    @api.model
    def action_update_date(self, domain_obj):
        of_mobile_days_before = (
            self.env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_before', 0)
        )
        of_mobile_days_after = (
            self.env['ir.config_parameter'].sudo().get_param('of_mobile.display_planning_days_after', 0)
        )

        now = fields.Datetime.now()
        today = fields.Date.today()
        before = today + relativedelta(days=-int(of_mobile_days_before))
        after = today + relativedelta(days=int(of_mobile_days_after))

        domain = [
            ('start', '>=', fields.Date.to_string(before)),
            ('start', '<=', fields.Date.to_string(after)),
            ('of_state', 'not in', ['cancel', 'postponed']),
        ]

        domain = expression.AND([domain, domain_obj])

        if interventions := self.env['calendar.event'].sudo().search(domain):
            interventions.write({'of_update_date': now})

    @api.depends('of_partner_id', 'of_address_id')
    def _compute_historical_ids(self):
        limit = self.env['ir.config_parameter'].sudo().get_param('of_mobile.history_limit')
        today = fields.Datetime.from_string(fields.Date.today())
        limit_date = today - relativedelta(months=int(limit))
        for interv in self:
            if interv.of_address_id:
                interventions = interv.of_address_id.of_intervention_address_ids
            elif interv.of_partner_id:
                interventions = interv.of_partner_id.of_intervention_partner_ids
            else:
                interv.of_historical_ids = False
                continue

            interv.of_historical_ids = interventions.filtered(
                lambda i: self._filterHistoricalIntervention(i, interv.start, limit_date)
            )

    def _filterHistoricalIntervention(self, historical_intervention, intervention_date, limit_date):
        return intervention_date > historical_intervention.start > limit_date

    @api.depends('of_partner_id', 'of_address_id')
    def _compute_coming_ids(self):
        for interv in self:
            if interv.of_address_id:
                interventions = interv.of_address_id.of_intervention_address_ids
            elif interv.of_partner_id:
                interventions = interv.of_partner_id.of_intervention_partner_ids
            else:
                interv.of_coming_ids = False
                continue

            interv.of_coming_ids = interventions.filtered(
                lambda i: self._filterComingIntervention(i, interv.start)
            ).sorted(key=lambda x: x.start)

    def _filterComingIntervention(self, coming_intervention, intervention_date):
        return intervention_date < coming_intervention.start

    def _is_intervention_today(self, intervention):
        # On considère qu'une intervention se déroule aujourd'hui
        # si la date du jour est comprise entre la date de début ou de fin

        today = fields.Date.from_string(fields.Date.today())
        start_date = fields.Date.from_string(intervention.start)
        end_date = fields.Date.from_string(intervention.stop)
        return start_date <= today <= end_date

    def action_mobile_create_invoice(self):
        """
        Create an invoice for the calendar event.
        """
        invoices = self.env['account.move']
        for event in self:
            if not event.of_fiscal_position_id:
                raise UserError(_("Intervention is non billable, please select a fiscal position."))

            # All lines are linked to order lines so they should be invoiced from the sale order
            if event.of_link_order and not event.of_line_ids.filtered(lambda li: not li.order_line_id):
                raise UserError(
                    _("Invoiceable lines are linked to order lines. Please do the invoicing from the sale order.")
                )

            if event.of_state not in ['confirmed', 'ongoing', 'done', 'unfinished', 'postponed']:
                raise UserError(_("Intervention is non billable because it must be confirmed."))

            # Prepare the invoice data
            invoice_data, messages = event._prepare_invoice()
            if invoice_data:
                move_obj = self.env['account.move']
                move = move_obj.create(invoice_data)
                move.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': move, 'origin': event},
                    subtype_id=self.env.ref('mail.mt_note').id,
                )
                invoices += move
        return invoices
