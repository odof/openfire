# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import math
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval

from odoo.addons.of_utils.models.misc import intervals_overlap


class OFServiceRequest(models.Model):
    """Service Request
    A service request is a request for intervention on a customer's site.
    That can be a request for maintenance, repair, installation, etc.

    There are two types of service requests:
        - punctual: a single intervention
        - recurrent: a series of interventions
    """

    _name = 'of.service.request'
    _inherit = 'mail.thread'
    _description = "Service Request"

    @api.model
    def _default_company(self):
        """For planning objects, the choice of company is made by settings in the company."""
        if self.company_id.of_company_choice == 'user':
            return self.env['res.company']._company_default_get('of.service.request')
        return False

    def _default_days(self):
        """Returns the days of the week from Monday to Friday as default"""
        days = self.env['of.days'].search([('number', 'in', (1, 2, 3, 4, 5))], order="number")
        return [day.id for day in days]

    @api.model
    def _domain_employee_ids(self):
        return ['|', ('of_is_operator', '=', True), ('of_is_salesperson', '=', True)]

    # ===== Service request fields =====
    active = fields.Boolean(default=True)
    name = fields.Char(compute='_compute_name', store=True)
    origin = fields.Char()
    number = fields.Char(copy=False)
    title = fields.Char()
    priority = fields.Selection(
        selection=[
            ('0', "Low"),
            ('1', "Normal"),
            ('2', "High"),
            ('3', "Very High"),
        ],
        index=True,
        default='0',
    )
    request_label_date = fields.Char(string="Date", compute='_compute_request_label_date')

    # States
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('nothing_to_plan', "Nothing To plan"),
            ('to_plan', "To plan"),
            ('to_plan_quickly', "To Plan Quickly"),
            ('planned', "Planned"),
            ('late', "Late for planning"),
            ('done', "Done"),
            ('part_planned', "Partially planned"),
            ('all_planned', "All planned"),
            ('cancel', "Cancelled"),
        ],
        string="Planning status",
        compute='_compute_state',
        store=True,
        help="Main state of the request. If the request is recurrent, the state is calculated from the interventions.",
    )
    base_state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('calculated', "Calculated"),
            ('cancel', "Cancelled"),
        ],
        string="Calculation status",
        default='draft',
        required=True,
        copy=False,
        help="This field is used to determine whether the request has been calculated or not.",
    )
    state_punctual = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('to_plan', "To plan"),
            ('part_planned', "Partially planned"),
            ('all_planned', "All planned"),
            ('late', "Late for planning"),
            ('done', "Done"),
            ('ongoing', "Ongoing intervention"),
            ('cancel', "Cancelled"),
        ],
        string="State",
        compute='_compute_state',
        store=True,
    )

    # Interventions
    intervention_ids = fields.One2many(
        comodel_name='calendar.event', inverse_name='of_request_id', string="Interventions"
    )
    intervention_count = fields.Integer(string="# Interventions", compute='_compute_intervention_count')
    template_id = fields.Many2one(comodel_name='of.planning.intervention.template', string="Intervention Template")

    # Type, tags and stage
    type_id = fields.Many2one(
        comodel_name='of.service.request.type',
        string="Type",
        compute='_compute_template_related_fields',
        store=True,
        readonly=False,
        required=True,
    )
    tag_ids = fields.Many2many(
        string="Tags",
        comodel_name='of.planning.tag',
        relation='of_service_request_planning_tag_rel',
        column1='request_id',
        column2='tag_id',
    )

    # History
    history_intervention_ids = fields.Many2many(
        comodel_name='calendar.event',
        column1='request_id',
        column2='event_id',
        relation='of_service_history_intervention_rel',
        compute='_compute_history_intervention_ids',
        string="History",
        help="Intervention history of the installed products. If no installed products, address history",
        store=True,
    )

    # Other linked resources
    task_id = fields.Many2one(
        comodel_name='of.planning.task',
        string="Task",
        compute='_compute_template_related_fields',
        store=True,
        readonly=False,
        required=True,
    )
    company_id = fields.Many2one(comodel_name='res.company', string="Company", required=True)
    user_id = fields.Many2one(comodel_name='res.users', string="User", default=lambda r: r.env.user)
    stage_id = fields.Many2one(
        comodel_name='of.service.request.stage',
        string="Stage",
        domain="[('type_ids','=',type_id)]",
        compute='_compute_stage_id',
        store=True,
        readonly=False,
        group_expand='_read_group_stage_ids',
    )
    employee_ids = fields.Many2many(
        comodel_name='hr.employee', string="Operators", domain=lambda self: self._domain_employee_ids()
    )
    last_attachment_id = fields.Many2one(
        comodel_name='ir.attachment', string="Last report", compute='_compute_last_attachment_id'
    )
    line_ids = fields.One2many(
        comodel_name='of.service.request.line',
        inverse_name='request_id',
        string="Invoice Lines",
        compute='_compute_line_ids',
        store=True,
        readonly=False,
    )

    # ===== Customer and address fields =====
    # Customer
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner", required=True, ondelete='restrict')

    # Address
    address_id = fields.Many2one(
        comodel_name='res.partner',
        string="Intervention Address",
        ondelete='restrict',
        compute='_compute_address_id',
        store=True,
        readonly=False,
    )
    address_address = fields.Char(string="Address", related='address_id.contact_address', readonly=True)
    address_street = fields.Char(string="Street", related='address_id.street', readonly=True)
    address_street2 = fields.Char(string="Street 2", related='address_id.street2', readonly=True)
    address_zip = fields.Char(string="Zip", related='address_id.zip', readonly=True)
    address_city = fields.Char(string="City", related='address_id.city', readonly=True)
    address_phone = fields.Char(string="Phone", related='address_id.phone', readonly=True)
    address_mobile = fields.Char(string="Mobile", related='address_id.mobile', readonly=True)
    address_email = fields.Char(string="Email", related='address_id.email', readonly=True)
    tech_sector_id = fields.Many2one(
        string="Tech Sector", related='address_id.of_tech_sector_id', readonly=True, store=True
    )
    department_id = fields.Many2one(
        comodel_name='res.country.department',
        string="Department",
        compute='_compute_department_id',
        readonly=True,
        store=True,
        compute_sudo=True,
    )

    # ===== Planning fields =====
    # Dates
    next_date = fields.Date(string="Next planning", help="Date from which to schedule the next intervention")
    last_next_date = fields.Date(help="Field to keep rollback capability")
    end_date = fields.Date(
        string="Planning end date",
        help="Date from which intervention becomes overdue",
        compute='_compute_end_date',
        store=True,
        readonly=False,
    )
    contract_end_date = fields.Date(string="Contract end date")
    # Duration
    duration = fields.Float(string="Estimated Duration", compute='_compute_duration', store=True, readonly=False)
    planned_duration = fields.Float(compute='_compute_durations', store=True)
    remaining_duration = fields.Float(compute='_compute_durations', store=True)

    # Recurrency
    recurrency = fields.Boolean(string="Recurring service request", default=False)
    recurring_rule_type = fields.Selection(
        selection=[('monthly', "Monthly"), ('yearly', "Yearly")],
        string="Recurrency",
        default='yearly',
        compute='_compute_recurring_rule_type',
        store=True,
        readonly=False,
        help="Specify the interval for automatic calculation of the next planning date for interventions.",
    )
    recurring_interval = fields.Integer(
        string="Repeat Every",
        help="Repeat (Months/Years)",
        default=1,
        compute='_compute_recurring_interval',
        store=True,
        readonly=False,
    )

    # Days and months
    day_ids = fields.Many2many(
        comodel_name='of.days',
        relation='of_service_request_days',
        column1='request_id',
        column2='day_id',
        string="Days",
        default=lambda self: self._default_days(),
        help="Customer availability days.",
    )
    month_ids = fields.Many2many(
        comodel_name='of.months',
        relation='of_service_request_months',
        column1='request_id',
        column2='month_id',
        string="Months",
        help="Planning reference months.",
    )

    # partner_id.category_id is a M2M field
    partner_tag_ids = fields.Many2many(string="Partner Tags", related='partner_id.category_id', readonly=True)

    # ===== Order fields =====
    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order",
        domain="['|', ('partner_id', 'child_of', partner_id), ('partner_id', 'parent_of', partner_id)]",
    )
    order_ids = fields.Many2many(comodel_name='sale.order', compute='_compute_order_ids', string="Orders", store=True)
    order_count = fields.Integer(string="# Orders", compute='_compute_order_ids', compute_sudo=True)

    # ===== Invoice and invoicing fields =====
    invoice_ids = fields.One2many(comodel_name='account.move', compute='_compute_invoice_ids', string="Invoices")
    invoice_count = fields.Integer(string="# Invoices", compute='_compute_invoice_ids')

    # ===== Currency and Pricing fields =====
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal Position",
        domain="[('tax_ids.tax_src_id.type_tax_use','=','sale')]",
        compute='_compute_fiscal_position_id',
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency', string="Currency", readonly=True, related='company_id.currency_id'
    )
    price_subtotal = fields.Monetary(compute='_compute_amounts', string="Subtotal", readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amounts', string="Taxes", readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amounts', string="Total", readonly=True, store=True)

    # ===== Description and notes fields =====
    note = fields.Text(string="Notes")
    map_view_display_note = fields.Text(
        string="Notes (displayed in Map view)", compute='_compute_map_view_display_note'
    )

    # ===== Misc. fields =====
    # Alerts
    is_recurring_task = fields.Boolean(string="Recurring Task", related='task_id.is_recurring', readonly=True)
    alert_dates = fields.Boolean(string="Inconsistent dates", compute='_compute_alert_dates')

    # Searching
    end_date_min = fields.Date(string="Min due date", compute=lambda *a, **k: {})
    end_date_max = fields.Date(string="Max due date", compute=lambda *a, **k: {})
    control_date = fields.Date(compute=lambda *a, **k: {})

    # Helper fields for views : tree, kanban, calendar, map
    partner_latitude = fields.Float(related='address_id.partner_latitude')
    partner_longitude = fields.Float(related='address_id.partner_longitude')
    precision = fields.Selection(related='address_id.of_precision')
    partner_name = fields.Char(related='partner_id.name')
    partner_mobile = fields.Char(related='partner_id.mobile')
    partner_phone = fields.Char(related='partner_id.phone')
    partner_email = fields.Char(related='partner_id.email')
    task_name = fields.Char(related='task_id.name', readonly=True)
    color = fields.Char(compute='_compute_color', help="Color of the request in the views")
    last_intervention_date = fields.Date(
        string="Last intervention Date",
        compute='_compute_last_intervention_date',
        store=True,
        help="Date of last appointment. Does not include cancelled or rescheduled appointments.",
    )

    # UX fields
    show_update_fpos = fields.Boolean(string="Has Fiscal Position Changed", store=False)

    # -----------------------------------------------------------------------
    # Constrains methods
    # -----------------------------------------------------------------------

    @api.constrains('next_date', 'end_date')
    def check_alert_dates(self):
        for request in self:
            if request.alert_dates:
                raise UserError(_("Intervention (%s): Inconsistent dates") % request.name)

    _sql_constraints = [
        (
            'duration_not_null_constraint',
            'CHECK ( duration > 0 )',
            _("Intervention duration must be greater than 0!"),
        ),
    ]

    # -----------------------------------------------------------------------
    # Compute methods
    # -----------------------------------------------------------------------

    @api.depends('address_id', 'partner_id', 'task_id')
    def _compute_name(self):
        for request in self:
            partner_name = request.partner_id.name or ""
            address_zip = request.address_id.zip or ""
            task_name = request.task_id.name or ""
            request.name = f"{task_name} {partner_name} {address_zip}"

    @api.depends(
        'base_state',
        'duration',
        'remaining_duration',
        'next_date',
        'last_next_date',
        'end_date',
        'contract_end_date',
        'recurrency',
        'intervention_ids',
        'intervention_ids.of_state',
    )
    def _compute_state(self):
        for request in self:
            if not request.next_date and not request.end_date:
                request.state = 'nothing_to_plan'
            else:
                request_state = request._get_state_from_date(fields.Date.context_today(self), to_plan_advance=True)
                if not request.recurrency and request.state_punctual != request_state:
                    request.state_punctual = request_state
                if request.state != request_state:
                    request.state = request_state

    @api.depends('intervention_ids', 'intervention_ids.of_state')
    def _compute_intervention_count(self):
        for request in self:
            request.intervention_count = len(
                request.intervention_ids.filtered(lambda r: r.of_state not in ('cancel', 'postponed'))
            )

    @api.depends(
        'intervention_ids',
        'intervention_ids.of_state',
        'intervention_ids.start_date',
    )
    def _compute_last_intervention_date(self):
        for request in self:
            old_intervention_date = request.last_intervention_date

            # do not take cancelled / postponed interventions
            interventions = request.intervention_ids.filtered(lambda i: i.of_state not in ('cancel', 'postponed'))
            last_intervention_date = interventions and interventions.sorted('start', reverse=True)[0].start or False
            if last_intervention_date != old_intervention_date:
                request.last_intervention_date = last_intervention_date

    @api.depends('task_id')
    def _compute_recurring_rule_type(self):
        for request in self:
            if request.task_id and request.task_id.is_recurring == request.recurrency:
                request.recurring_rule_type = request.task_id.recurring_rule_type

    @api.depends('task_id')
    def _compute_recurring_interval(self):
        for request in self:
            if request.task_id and request.task_id.is_recurring == request.recurrency:
                request.recurring_interval = request.task_id.recurring_interval

    @api.depends('task_id')
    def _compute_fiscal_position_id(self):
        for request in self:
            if request.task_id and request.task_id.fiscal_position_id and not request.fiscal_position_id:
                request.fiscal_position_id = request.task_id.fiscal_position_id
            if request.fiscal_position_id:
                request._recompute_taxes()

    @api.depends('task_id')
    def _compute_line_ids(self):
        for request in self:
            if (
                request.task_id
                and request.task_id.product_id
                and (not request.template_id or request.template_id.task_id != request.task_id)
            ):
                request.line_ids = [
                    Command.create(
                        {
                            'request_id': request.id,
                            'product_id': request.task_id.product_id.id,
                            'qty': 1,
                            'price_unit': request.task_id.product_id.lst_price,
                            'name': request.task_id.product_id.name,
                        }
                    )
                ]

            request._recompute_taxes()

    @api.depends('task_id')
    def _compute_duration(self):
        for request in self:
            if request.task_id and not request.duration:
                request.duration = request.task_id.duration

    @api.depends('task_id', 'next_date')
    def _compute_end_date(self):
        for request in self:
            request.end_date = self._get_end_date()

    @api.depends(
        'duration',
        'intervention_ids',
        'recurrency',
        'intervention_ids.of_state',
        'next_date',
        'month_ids',
        'task_id',
        'intervention_ids.start_date',
    )
    def _compute_durations(self):
        for request in self:
            events = request.intervention_ids.filtered(lambda p: p.of_state not in ('cancel', 'postponed'))

            if request.recurrency and request.next_date:
                # On cherche la durée planifiée pour l'occurrence en cours.
                # Il nous faut savoir quelle est l'occurrence en cours
                date_next_ref = request._get_date_close(fields.Date.today())  # début d'occurrence en cours
                date_end_ref = request._get_end_date(date_next_ref)  # fin d'occurrence en cours

                # RDVs pris en avance.
                # Récupération de date de fin de l'occurrence précédente pour connaître l'écart entre les deux et le
                # couper en deux.
                # - Tous les RDVs de la 1ere moitié sont des RDVs en retard de l'occurrence précédente et ne sont pas à
                # prendre en compte dans la durée planifiée.
                # - Tous les RDVs de la 2eme moitié sont des RDVs en avance de l'occurrence en cours.
                date_next_previous = request._get_next_date(date_next_ref, forward=False)
                date_end_previous = request._get_end_date(date_next_previous)
                diff_previous = (date_next_ref - date_end_previous) / 2
                date_advance = date_next_ref - diff_previous

                # RDVs pris en retard, même principe que pour les RDVs pris en avance
                date_next_next = request._get_next_date(date_next_ref, forward=True)
                diff_next = (date_next_next - date_end_ref) / 2
                date_late = date_next_ref + diff_next

                # Sélection des RDVs de l'occurrence en cours
                events = events.filtered(lambda p: date_advance <= p.start.date() < date_late)

            request.planned_duration = sum(events.mapped('duration'))
            request.remaining_duration = (
                request.duration > request.planned_duration and request.duration - request.planned_duration or 0
            )

    @api.depends('template_id', 'base_state')
    def _compute_template_related_fields(self):
        """Compute the fields related to the template."""
        for request in self.filtered(lambda r: r.base_state == 'draft' and r.template_id):
            lines_to_create = []
            request.task_id = request.template_id.task_id
            if request.template_id.task_id.product_id:
                lines_to_create.append(
                    Command.create(
                        {
                            'request_id': request.id,
                            'product_id': request.template_id.task_id.product_id.id,
                            'qty': 1,
                            'price_unit': request.template_id.task_id.product_id.lst_price,
                            'name': request.template_id.task_id.product_id.name,
                        }
                    )
                )

            request.type_id = request.template_id.type_id
            request.fiscal_position_id = request.template_id.fiscal_position_id or request.fiscal_position_id
            lines_to_create.extend(
                Command.create(line._prepare_request_service_line_vals(request))
                for line in request.template_id.line_ids
            )
            if lines_to_create:
                request.line_ids = lines_to_create
                request._recompute_taxes()

    def _search_remaining_duration(self, operator, operand):
        requests = self.search([])
        res = safe_eval(
            "requests.filtered(lambda s: s.remaining_duration %s %.2f)" % (operator, operand), {'requests': requests}
        )
        return [('id', 'in', res.ids)]

    @api.depends('next_date', 'end_date')
    def _compute_alert_dates(self):
        for request in self:
            request.alert_dates = request.next_date and request.end_date and request.next_date > request.end_date

    @api.depends('state')
    def _compute_color(self):
        """Color of Request in the views. Color is based on the request's state.
        Colors description and meaning:
            - grey  : request whose address has no GPS coordinates, or inactive request
            - orange: request to be planned or partially planned
            - red : request late for planning
            - black  : other requests"""
        for request in self:
            if request.state in ('to_plan', 'planned', 'progress', 'done', 'part_planned', 'all_planned'):
                request.color = 'black'
            elif request.state in ('to_plan_quickly'):
                request.color = 'orange'
            elif request.state == 'late':
                request.color = 'red'
            else:
                request.color = 'grey'

    @api.depends('line_ids', 'line_ids.order_line_id')
    def _compute_order_ids(self):
        for request in self:
            request.order_ids = request.mapped('line_ids.order_line_id.order_id')
            request.order_count = len(request.order_ids)

    @api.depends(
        'line_ids',
        'line_ids.invoice_line_ids',
        'order_ids',
        'order_ids.invoice_ids',
        'line_ids.invoice_line_ids.move_id',
    )
    def _compute_invoice_ids(self):
        for request in self:
            invoices = request.mapped('line_ids.invoice_line_ids.move_id')
            invoices |= request.mapped('order_ids.invoice_ids')
            request.invoice_count = len(invoices)
            request.invoice_ids = invoices

    @api.depends('address_id.of_intervention_address_ids', 'partner_id.of_intervention_address_ids')
    def _compute_history_intervention_ids(self):
        event_obj = self.env['calendar.event']
        for request in self:
            if partner := request.address_id or request.partner_id:
                history_interventions = event_obj.search([('of_address_id', '=', partner.id)])
                request.history_intervention_ids = history_interventions

    def _compute_request_label_date(self):
        for request in self:
            interventions = request.intervention_ids.filtered(lambda i: i.of_state not in ('cancel', 'postponed'))
            if request.state == 'done' and interventions:
                request.request_label_date = _("Completed on %s") % format_date(
                    self.env, request.intervention_ids[-1].start_date
                )
            elif interventions:
                request.request_label_date = _("Scheduled for %s") % format_date(
                    self.env, request.intervention_ids[-1].start_date
                )
            else:
                request.request_label_date = _("Scheduled between %s and %s") % (
                    format_date(self.env, request.next_date),
                    format_date(self.env, request.end_date),
                )

    def _compute_last_attachment_id(self):
        """Retrieves the Intervention sheet report of the last intervention having said report in attachments"."""
        attachment_obj = self.env['ir.attachment']
        for request in self:
            if request.intervention_ids.filtered(lambda i: i.state not in ('cancel', 'postponed')):
                for i in range(1, len(request.intervention_ids) + 1):
                    current_intervention = request.intervention_ids[-i]
                    if attachment := attachment_obj.search(
                        [
                            ('res_model', '=', 'calendar.event'),
                            ('res_id', '=', current_intervention.id),
                            ('of_intervention_report', '=', True),
                        ]
                    ):
                        request.last_attachment_id = attachment[-1]
                        break

    @api.depends('line_ids', 'line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_amounts(self):
        for request in self:
            request.price_subtotal = sum(request.line_ids.mapped('price_subtotal'))
            request.price_tax = sum(request.line_ids.mapped('price_tax'))
            request.price_total = sum(request.line_ids.mapped('price_total'))

    @api.depends('partner_id.country_department_id', 'address_id.country_department_id')
    def _compute_department_id(self):
        for request in self:
            if request.address_id:
                request.department_id = request.address_id.country_department_id
            elif request.partner_id:
                request.department_id = request.partner_id.country_department_id

    def _compute_map_view_display_note(self):
        for rec in self:
            rec.map_view_display_note = rec.note and rec.note[:300] or ""

    @api.depends('partner_id')
    def _compute_address_id(self):
        for request in self:
            if request.partner_id and not request.address_id:
                addresses = request.partner_id.address_get(['delivery'])
                request.address_id = addresses['delivery']

    @api.depends('type_id')
    def _compute_stage_id(self):
        for request in self:
            if request.type_id and request.type_id.stage_ids:
                request.stage_id = request.type_id.stage_ids[0]

    # -----------------------------------------------------------------------
    # Onchange methods
    # -----------------------------------------------------------------------

    @api.onchange('fiscal_position_id')
    def _onchange_fpos_id_show_update_fpos(self):
        if self.line_ids and (
            not self.fiscal_position_id or self._origin.fiscal_position_id != self.fiscal_position_id
        ):
            self.show_update_fpos = True

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id and self.type_id != self.template_id.type_id:
            self.template_id = False

    # -----------------------------------------------------------------------
    # ORM methods
    # -----------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('address_id') and not vals.get('partner_id'):
                address = self.env['res.partner'].browse(vals['address_id'])
                partner = address.parent_id or address
                vals['partner_id'] = partner.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('base_state') == 'calculated':
            self._affect_service_request_number()
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        res = stages.search([], order=order)
        if self._context.get('of_kanban_steps') == "Maintenance":
            if maintenance_type := self.env.ref(
                'of_service.of_service_request_type_maintenance', raise_if_not_found=False
            ):
                return res.filtered(lambda s: maintenance_type.id in s.type_ids.ids)
        return res

    def name_get(self):
        if not self._context.get('service_request_extended_name_display'):
            return super().name_get()
        return [
            (
                request.id,
                f"{request.number or ''}{' - ' if request.number else ''}{request.name}",
            )
            for request in self
        ]

    # -----------------------------------------------------------------------
    # Actions methods
    # -----------------------------------------------------------------------

    def action_button_create_intervention(self):
        wizard = self.env['of.service.request.create.intervention.wizard'].create(
            {'line_ids': [Command.create({'request_id': request.id}) for request in self]}
        )
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'of.service.request.create.intervention.wizard',
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_button_view_intervention(self):
        action = self.env.ref('of_planning.action_calendar_event').sudo().read()[0]
        if len(self.ids) == 1:
            action['context'] = self._get_action_view_intervention_context(safe_eval(action['context']))
        if len(self.intervention_ids) == 1:
            action['res_id'] = self.intervention_ids.ids[0]
        return self.mapped('intervention_ids')._get_calendar_event_action_views(action)

    def action_button_view_order(self):
        self.ensure_one()
        orders = self.order_ids
        action = self.env.ref('sale.action_orders').read()[0]
        if len(orders) > 1:
            action['domain'] = [('id', 'in', orders.ids)]
        elif len(orders) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = orders.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_button_view_invoice(self):
        self.ensure_one()
        invoices = self.invoice_ids
        action = self.env.ref('account.view_out_invoice_tree').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_button_request_send_mail(self):
        self.ensure_one()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model='of.service.request',
            default_res_id=self.id,
            default_composition_mode='comment',
        )
        # add mail template if exists
        if template := self.env.ref('of_service.email_template_of_service_request', raise_if_not_found=False):
            ctx['default_template_id'] = template.id
            ctx['default_use_template'] = bool(template.id)
        return {
            'name': _("Compose Email"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_button_open_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_planning.action_calendar_event').read()[0]
        interventions = self.intervention_ids
        if len(interventions) > 1:
            action['context'] = {'search_default_of_request_id': self.id}
        elif len(interventions) == 1:
            action['views'] = [(self.env.ref('of_planning.calendar_event_view_form').id, 'form')]
            action['res_id'] = interventions.ids[0]
        return action

    def action_button_validate(self):
        self.write({'base_state': 'calculated'})

    def action_button_cancel(self):
        self.write({'base_state': 'cancel'})

    def action_button_draft(self):
        self.write({'base_state': 'draft'})

    def action_button_update_taxes(self):
        self.ensure_one()

        self._recompute_taxes()

        self.message_post(
            body=_(
                "Product taxes have been recomputed according to fiscal position %s.",
                self.fiscal_position_id._get_html_link() if self.fiscal_position_id else "",
            )
        )

    # -----------------------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------------------

    @api.model
    def _get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval, day=1)  # 1er du mois
        else:
            return relativedelta(years=interval, day=1)  # 1er du mois

    def _get_date_close(self, date_eval):
        """
        Calculate the closest allowed date based on the given evaluation date.

        :param date_eval (datetime.date): The evaluation date.
        :return (datetime.date): The closest allowed closing date.
        """
        self.ensure_one()
        if not self.recurrency:
            return

        month_ints = self.mapped('month_ids.number') or range(1, 13)

        date_eval_month_int = date_eval.month
        if date_eval_month_int in month_ints:  # la date est déjà sur un mois autorisé
            return date(year=date_eval.year, month=date_eval_month_int, day=1)

        current_month_int = date_eval_month_int
        # Détection du mois précédent et du mois suivant dans la DI (valeur 1-12)
        past_month_int = month_ints[-1]
        futur_month_int = month_ints[0]
        for month_int in month_ints:
            if month_int < current_month_int:
                past_month_int = month_int
            else:
                futur_month_int = month_int
                break

        # Modification des mois : valeur de -11 à +24 selon l'année
        if past_month_int > date_eval_month_int:
            past_month_int -= 12
        if futur_month_int < date_eval_month_int:
            futur_month_int += 12

        # Mois le plus proche de la date fournie
        month_int = past_month_int if past_month_int + futur_month_int > 2 * date_eval_month_int else futur_month_int
        month_int -= 1

        # A ce stade, month_int est un numéro de mois de 0 à 11 auquel a été ajouté/retiré 12 en fonction de l'année.
        # Il ne reste donc plus qu'à calculer l'année et le mois réels.
        year_int = date_eval.year + int(math.floor(month_int / 12.0))
        month_int = month_int % 12 + 1

        return date(year_int, month_int, 1)

    def _get_next_date(self, date_str, forward=True):
        """
        Compute the next date based on the given date and the recurring rule.
        :params: date_str (str): The date string to compute the next date from.
        :params: forward (bool, optional): If True, compute the next date in forward mode.
            If False, compute the next date in backward mode. Defaults to True.
        :return: datetime.date: The computed next date.
        :raises: UserError: If there is no date to compute the next date from.
        """
        self.ensure_one()
        if not self.recurrency:
            return False

        month_ints = self.mapped('month_ids.number') or range(1, 13)

        if forward:
            # si mode forward, l'occurence par défaut à étudier est dernière
            date_from = max(date_str, self.last_intervention_date)
        else:
            # si mode backward, l'occurence par défaut à étudier est la prochaine
            date_from = min(date_str, self.next_date)

        if not date_from:
            raise UserError(_("No date to compute next date from"))

        date_from = self._get_date_close(date_from)

        if forward:
            date_to = date_from + self._get_relative_delta(self.recurring_rule_type, self.recurring_interval)
            date_to_month_int = date_to.month
            # générer les mois de l'année suivante pour faciliter calcul du mois et de l'année du résultat
            month_int_temp = list(month_ints) + [m + 12 for m in month_ints]
            res_month_int = min(month_int_temp, key=lambda month: (abs(month - date_to_month_int), month))
            if res_month_int > 12:
                res_next_year = True
                res_month_int -= 12
            else:
                res_next_year = False
            res_year_int = date_to.year + res_next_year

        else:
            date_to = date_from - self._get_relative_delta(self.recurring_rule_type, self.recurring_interval)
            date_to_month_int = date_to.month
            # générer les mois de l'année précédente pour faciliter calcul du mois et de l'année du résultat
            month_int_temp = list(month_ints) + [m - 12 for m in month_ints]
            res_month_int = min(month_int_temp, key=lambda month: (abs(month - date_to_month_int), month))
            if res_month_int < 1:
                res_last_year = True
                res_month_int += 12
            else:
                res_last_year = False
            res_year_int = date_to.year - res_last_year

        return date(year=res_year_int, month=res_month_int, day=1)

    def _get_end_date(self, specified_next_date=False):
        """Returns the end date from which intervention becomes overdue"""
        self.ensure_one()
        if not (next_date := specified_next_date or self.next_date or False):
            return False

        end_date = next_date
        if self.template_id and self.template_id.planning_granularity:
            if self.template_id.planning_granularity == 'weekly':
                end_date += relativedelta(weeks=1)
            elif self.template_id.planning_granularity == 'fortnightly':
                end_date += relativedelta(weeks=2)
            elif self.template_id.planning_granularity == 'monthly':
                end_date += relativedelta(months=1)
        elif self.recurrency:
            end_date += relativedelta(months=1)  # one month for recurring task (as sweeping/maintenance task)
        else:
            end_date += relativedelta(weeks=2)
        end_date -= relativedelta(days=1)  # remove one day because date ranges are inclusive
        return end_date

    def _prepare_sale_order_values(self):
        self.ensure_one()
        return {
            'partner_id': self.partner_id.id,
            'origin': self.number,
            'fiscal_position_id': self.fiscal_position_id.id,
            'order_line': [Command.create(line._prepare_so_line_vals()) for line in self._get_orderable_lines()],
        }

    def _make_sale_order(self):
        """Creates a sale order from the service request.

        :return: Action to open the created sale order
        """
        self.ensure_one()

        order_obj = self.env['sale.order']
        order_line_obj = self.env['sale.order.line']

        # Do not create an order if the Service Request is not validated
        if self.base_state != 'calculated':
            return self.env['of.popup.wizard'].popup_return(message=_("This service request is not validated."))

        # Do not create order if no lines
        if not self.line_ids:
            return self.env['of.popup.wizard'].popup_return(message=_("This service request has no lines."))

        # Do not create an order if all lines are already associated with an order
        if not self.line_ids.filtered(lambda li: not li.order_line_id):
            return self.env['of.popup.wizard'].popup_return(
                message=_("All lines are already associated with an order.")
            )

        # Do not create an order if all lines are already associated with one or more invoices.
        if not self.line_ids.filtered(lambda li: not li.invoice_line_ids):
            return self.env['of.popup.wizard'].popup_return(
                message=_("All lines are already associated with one or more invoices.")
            )

        # Do not create an order if the fiscal position is not filled in.
        if not self.fiscal_position_id:
            return self.env['of.popup.wizard'].popup_return(message=_("Please enter a fiscal position."))

        # Create sale order
        order = order_obj.create(self._prepare_sale_order_values())

        # Connect lines to their corresponding order line
        request_lines = self.line_ids.filtered(lambda li: not li.order_line_id and not li.invoice_line_ids)
        created_order_lines = order_line_obj.search([('of_request_line_id', 'in', request_lines.mapped('id'))])
        for line in request_lines:
            order_lines = created_order_lines.filtered(lambda order_line: order_line.of_request_line_id == line)
            line.order_line_id = order_lines and order_lines[0].id or False
        return {
            'name': _("Order"),
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': order.id,
        }

    def _get_orderable_lines(self):
        """Returns the lines of the service request that can be added to a sale order."""
        self.ensure_one()
        return self.line_ids.filtered(lambda line: not line.order_line_id and not line.invoice_line_ids)

    def _compute_state_from_date_for_recurrency(self, date_eval, to_plan_advance, next_date, end_date, last_next_date):
        """Computes the state of recurring service request based on the given dates.

        :param: datetime date_eval: The date to evaluate the state for.
        :param: bool to_plan_advance: Flag indicating whether to plan in advance or not.
        :param: datetime next_date: The next planned date.
        :param: datetime end_date: The end date of the recurring request.
        :param: datetime last_next_date: The date of the last planned intervention.

        :return: The state of the recurring request. Possible values are:
            - 'done': The request has expired before the given date or before the next plan date.
            - 'to_plan': The planning range and the given dates overlap, no intervention has been planned,
                            and the last intervention is more than a month ago.
            - 'to_plan_quickly': The last intervention is less than a month after the given date.
            - 'planned': The last intervention was less than a month before the given date.
            - 'late': The end of the next planning is before the given date.
            - 'progress': None of the above conditions are met, indicating the request is still in progress.
        :rtype: str
        """
        one_month_ago = date_eval - relativedelta(months=1)
        in_one_month = date_eval + relativedelta(months=1)

        end_to_plan = to_plan_advance and in_one_month or date_eval
        contract_end_date = self.contract_end_date or False
        if contract_end_date and (contract_end_date < next_date or contract_end_date < date_eval):
            return 'done'
        elif intervals_overlap(next_date, end_date, date_eval, end_to_plan, strict=False) and (
            not last_next_date or last_next_date < one_month_ago
        ):
            return 'to_plan'
        elif last_next_date and (date_eval < last_next_date <= in_one_month):
            return 'to_plan_quickly'
        elif last_next_date and (one_month_ago <= last_next_date <= date_eval):
            return 'planned'
        elif end_date < date_eval:
            return 'late'
        return 'progress'

    def _compute_state_from_date(self, date_eval, end_date, last_next_date):
        """
        Computes the state of the service request based on the given dates.

        :param datetime date_eval: The date to evaluate the state.
        :param datetime end_date: The end date of the service request.
        :param datetime last_next_date: The date of the last planned intervention.

        :return: The state of the service request. Possible values are:
            - 'late': The remaining duration is not zero and the end date has passed.
            - 'to_plan': No intervention has been planned yet.
            - 'done': The remaining duration is zero and the last planned intervention has passed.
            - 'all_planned': The remaining duration is zero and the last planned intervention is in the future.
            - 'part_planned': The remaining duration is not zero and the end date is in the future.
        :rtype: str
        """
        if end_date < date_eval and self.remaining_duration != 0:
            return 'late'
        elif not last_next_date:
            # remaining_duration == 0 and the last scheduled intervention has passed: 'done'
            return 'to_plan'
        elif self.remaining_duration == 0 and last_next_date < date_eval:
            return 'done'
        elif self.remaining_duration == 0 and self.duration:
            return 'all_planned'
        return 'part_planned'

    def _get_state_from_date(self, date_eval=fields.Date.today(), to_plan_advance=False):
        """Calculates the status of an intervention at a given date, intended to be used for non passed dates.
        The status is calculated from the next_date field and the end_date field.

        :param date date_eval: Date on which we want to know the status of interventions,
            defaults to fields.Date.today()
        :param boolean to_plan_advance: Consider that an intervention is 'to_plan' 1 month before its `next_date`,
            defaults to False
        :return: Intervention status at the given date
        :rtype: str
        """
        self.ensure_one()

        if self.base_state and self.base_state == 'calculated':
            # self.base_state = 'cancelled' and self.base_state = 'draft' states are triggered manually.
            # 'next_date' field corresponds to start date of the planning range and the 'end_date' field corresponds
            # to end date of the planning range
            next_date = self.next_date
            last_next_date = self.last_next_date or False
            end_date = self.end_date or next_date + relativedelta(days=13)
            return (
                self._compute_state_from_date_for_recurrency(
                    date_eval, to_plan_advance, next_date, end_date, last_next_date
                )
                if self.recurrency
                else self._compute_state_from_date(date_eval, end_date, last_next_date)
            )
        else:
            return self.base_state

    def _get_action_view_intervention_context(self, action_context=None):
        """Returns the context to open the intervention view from the service request.

        :param action_context: dict action context, defaults to None
        :return: dict action context
        """
        if action_context is None:
            action_context = {}

        default_start = fields.Datetime.now().replace(  # default start date is the next_date at 8:00
            day=self.next_date.day, month=self.next_date.month, year=self.next_date.year, hour=7, minute=0, second=0
        )
        default_stop = default_start + relativedelta(hours=self.duration)
        action_context.update(
            {
                'default_of_partner_id': self.partner_id.id,
                'default_of_address_id': self.address_id and self.address_id.id or self.partner_id.id,
                'default_of_task_id': self.task_id and self.task_id.id or False,
                'default_start': default_start,
                'default_stop': default_stop,
                'default_duration': self.duration,
                'default_of_tag_ids': [Command.set([tag.id for tag in self.tag_ids])],
                'default_of_internal_description': self.note,
                'default_of_request_id': self.id,
                'search_default_of_request_id': self.id,
                'create': self.base_state == 'calculated',
                'edit': self.base_state == 'calculated',
                'default_of_order_id': self.order_id and self.order_id.id or False,
                'default_of_fiscal_position_id': self.fiscal_position_id and self.fiscal_position_id.id or False,
                'default_of_template_id': self.template_id and self.template_id.id or False,
                'default_of_employee_ids': [Command.set([employee.id for employee in self.employee_ids])],
            }
        )
        if self.base_state != 'calculated' or self.state == 'done':
            # Inhibit creation in calendar view if the job cannot be scheduled (draft, cancelled, completed)
            action_context['inhibit_create'] = True
            message_detail = (
                _("an intervention who is done")
                if self.state == 'done'
                else (
                    self.base_state == 'cancel'
                    and _("an intervention who is cancelled")
                    or _("an intervention who is not confirmed")
                )
            )
            action_context['inhibit_create'] = _("You cannot create an appointment for %s.") % message_detail
        if self.line_ids:
            # Generating the lines here did not work, so we indicate in the context that they should be generated.
            # They will then be generated in the onchange_request_id
            action_context['of_import_request_lines'] = True

        return action_context

    def _affect_service_request_number(self):
        for request in self.filtered(lambda r: r.base_state == 'calculated' and not r.number):
            request.write({'number': self.env['ir.sequence'].next_by_code('of.service.request')})

    def _recompute_taxes(self):
        self.ensure_one()
        self.line_ids._compute_tax_ids()
        self.show_update_fpos = False

    def _get_service_request_action_views(self, action):
        """Helper method to add the tree in first position view to the given action.
        :return: dict with the updated action
        """
        request_count = len(self)
        if request_count == 1:
            views = [(self.env.ref('of_service_request_view_form', raise_if_not_found=False).id, 'form')]
            views.extend(view for view in action['views'] if view[1] != 'form')
            action['views'] = views
            return action
        else:
            if tree_view := self.env.ref('of_service_request_view_tree', raise_if_not_found=False):
                views = [(tree_view.id, 'tree')]
                views.extend(view for view in action['views'] if view[1] != 'tree')
                action['views'] = views
        return action
