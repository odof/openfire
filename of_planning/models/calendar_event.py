# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event', 'of.readgroup']

    @api.model
    def _domain_employee_ids(self):
        return ['|', ('of_is_operator', '=', True), ('of_is_salesperson', '=', True)]

    name = fields.Char(required=False)
    # ===== Intervention specifics fields =====
    of_state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('confirmed', "Confirmed"),
            ('ongoing', "Ongoing"),
            ('unfinished', "Unfinished"),
            ('done', "Done"),
            ('cancel', "Cancelled"),
            ('postponed', "Postponed"),
        ],
        string="State",
        index=True,
        readonly=True,
        default='draft',
        tracking=True,
    )
    of_type = fields.Selection(
        selection=[
            ('intervention', "Intervention"),
            ('event', "Event"),
        ],
        string="Event Type",
        index=True,
        default='intervention',
        required=True,
        help="Technical field to differentiate between interventions and events",
    )
    of_is_closed = fields.Boolean(string="Closed", default=False, tracking=True)
    of_number = fields.Char(string="Number", copy=False)
    of_company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        compute='_compute_of_company_id',
        store=True,
        readonly=False,
    )
    of_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal position",
        compute='_compute_of_fiscal_position_id',
        store=True,
        readonly=False,
    )
    of_tag_ids = fields.Many2many(
        comodel_name='of.planning.tag', column1='intervention_id', column2='tag_id', string="Intervention Tags"
    )
    of_line_ids = fields.One2many(
        comodel_name='of.planning.intervention.line',
        inverse_name='intervention_id',
        string="Invoice lines",
        compute='_compute_of_line_ids',
        store=True,
        readonly=False,
    )

    # ===== Team, Operators, Employees, Resource fields =====
    of_resource_id = fields.Many2one(
        comodel_name='resource.resource',
        string="Resource",
        compute='_compute_of_resource_id',
        store=True,
        readonly=False,
        help="Resource linked to the intervention",
    )
    of_team_id = fields.Many2one(comodel_name='of.planning.team', string="Team")
    of_employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        relation='of_employee_intervention_rel',
        column1='intervention_id',
        column2='employee_id',
        compute='_compute_of_employee_ids',
        store=True,
        readonly=False,
        string="Operators",
        domain=lambda self: self._domain_employee_ids(),
        copy=False,
    )
    partner_ids = fields.Many2many(compute='_compute_partner_ids', readonly=False, store=True)
    of_employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Main operator",
        readonly=False,
        domain=lambda self: self._domain_employee_ids(),
        copy=False,
    )
    of_category_id = fields.Many2one(comodel_name='hr.employee.category', string="Employee category")

    # ===== Customer and address fields =====
    # Customer
    of_partner_id = fields.Many2one(comodel_name='res.partner', string="Customer", ondelete='restrict')
    of_partner_tag_ids = fields.Many2many(
        comodel_name='res.partner.category',
        string="Customer tags",
        related='of_partner_id.category_id',
        readonly=True,
    )
    of_partner_category_ids = fields.Many2many(
        comodel_name='res.partner.category',
        string="Customer category",
        related='of_partner_id.category_id',
        readonly=True,
    )
    of_email = fields.Char(string="Email", related='of_partner_id.email')
    of_mobile = fields.Char(related='of_partner_id.mobile')
    of_phone = fields.Char(related='of_partner_id.phone')
    of_partner_pricelist_id = fields.Many2one(
        comodel_name='product.pricelist', string="Pricelist", related='of_partner_id.property_product_pricelist'
    )
    of_history_intervention_ids = fields.One2many(
        comodel_name='calendar.event', compute='_compute_of_history_intervention_ids', string="History"
    )
    # Address
    of_address_id = fields.Many2one(
        comodel_name='res.partner',
        string="Address",
        compute='_compute_of_address_id',
        store=True,
        readonly=False,
        tracking=True,
        auto_join=True,
    )
    of_geocoding_state = fields.Selection(string="Geocoding state", related='of_address_id.of_geocoding_state')
    of_address_street = fields.Char(related='of_address_id.street', string="Street", readonly=True)
    of_address_street2 = fields.Char(related='of_address_id.street2', string="Street 2", readonly=True)
    of_address_city = fields.Char(related='of_address_id.city', string="City", readonly=True)
    of_address_zip = fields.Char(related='of_address_id.zip', string="Zip", readonly=True)
    of_address_phone_number_ids = fields.One2many(related='of_address_id.of_phone_number_ids', readonly=True)
    of_sector_id = fields.Many2one(related='of_address_id.of_tech_sector_id', string="Sector", readonly=True)
    of_department_id = fields.Many2one(
        comodel_name='res.country.department',
        related='of_address_id.country_department_id',
        string="Department",
        readonly=True,
        store=True,
        compute_sudo=True,
    )

    # ===== Order fields =====
    of_order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order",
        copy=False,
        domain="['|', ('partner_id', '=', of_partner_id), ('partner_id', '=', of_address_id)]",
    )
    of_order_amount_total = fields.Monetary(
        string="Order amount", currency_field='of_currency_id', readonly=True, compute='_compute_order_amounts'
    )
    of_order_still_due = fields.Monetary(
        string="Order still due amount",
        currency_field='of_currency_id',
        readonly=True,
        compute='_compute_order_amounts',
    )
    of_link_order = fields.Boolean(string="Invoicing on order", compute='_compute_of_link_order', store=True)

    # ===== Invoice and invoicing fields =====
    of_invoice_policy = fields.Selection(
        selection=[('delivery', "Delivered quantity"), ('intervention', "Planned quantity")],
        string="Invoice policy",
        default='intervention',
    )
    of_invoice_status = fields.Selection(
        selection=[
            ('no', "Nothing to Bill"),
            ('to invoice', "Waiting Bills"),
            ('invoiced', "Fully Billed"),
        ],
        string="Invoice status",
        compute='_compute_of_invoice_status',
        store=True,
    )
    of_invoice_ids = fields.One2many(comodel_name='account.move', string="Invoices", compute='_compute_invoice_ids')
    of_invoice_count = fields.Integer(string="# Invoices", compute='_compute_invoice_ids')

    # ===== Delivery fields =====
    of_picking_ids = fields.One2many(
        comodel_name='stock.picking', string="Linked pickings", compute='_compute_pickings'
    )
    of_delivery_count = fields.Integer(string="# Pickings", compute='_compute_pickings')
    of_picking_amount_total = fields.Monetary(
        string="Linked picking total amount",
        readonly=True,
        compute='_compute_picking_amounts',
        currency_field='of_currency_id',
    )
    of_picking_domain = fields.Many2many(comodel_name='stock.picking', compute='_compute_of_picking_domain')
    of_picking_manual_ids = fields.Many2many(
        comodel_name='stock.picking',
        string="Stock picking (manual)",
        relation='of_planning_intervention_picking_manual_rel',
        column1='intervention_id',
        column2='picking_id',
    )
    of_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string="Warehouse", default=lambda self: self._default_of_warehouse_id()
    )
    of_procurement_group_id = fields.Many2one(comodel_name='procurement.group', string="Procurement Group", copy=False)

    # ===== Planning fields =====
    of_task_id = fields.Many2one(
        comodel_name='of.planning.task', string="Task", compute='_compute_of_task_id', store=True, readonly=False
    )
    of_template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template', string="Intervention template", change_default=True
    )
    of_force_dates = fields.Boolean(string="Force dates", default=False, help="/!\\ overwrite operator's schedule")

    # ===== Description and notes fields =====
    of_internal_description = fields.Text(string="Internal description")
    of_intervention_notes = fields.Html(
        string="Intervention notes",
        related='of_order_id.of_intervention_notes',
        readonly=True,
        help="These notes are taken from the quote/order under the heading 'Intervention notes'. "
        "They can only be modified in the quote/order (see the associated order).",
    )
    of_customer_notes = fields.Html(
        related='of_partner_id.comment',
        string="Customer notes",
        readonly=True,
        help="These notes are taken from the customer master record under 'Internal notes'. "
        "They can only be modified in the customer record.",
    )
    of_minutes = fields.Text(string="Minutes", copy=False, help="Minutes of the intervention")
    of_previous_minutes = fields.Text(
        string="Previous intervention's minutes",
        compute='_compute_of_previous_minutes',
        help="Minutes of the previous intervention",
    )

    # ===== Duration & time fields =====
    start = fields.Datetime(default=lambda self: fields.Datetime.now().replace(second=0))
    stop = fields.Datetime(default=lambda self: fields.Datetime.now().replace(second=0) + timedelta(hours=1))
    of_real_start = fields.Datetime(string="Real start", copy=False)
    of_real_stop = fields.Datetime(string="Real stop", copy=False)
    of_real_duration = fields.Float(string="Real duration", compute='_compute_of_real_duration', store=True, copy=False)
    of_break_duration = fields.Float(string="Break duration", copy=False)
    of_break_start = fields.Datetime(string="Break start", store=True, copy=False)
    of_in_break = fields.Boolean(string="In break", compute='_compute_of_in_break', store=True)
    of_travel_duration = fields.Float(string="Travel duration", copy=False)
    of_total_duration = fields.Float(string="Total duration", compute='_compute_of_total_duration', store=True)

    # ===== Signature fields =====
    of_customer_signature = fields.Image(string="Customer's signature", copy=False, max_width=256, max_height=256)
    of_operator_signature = fields.Image(string="Operator's signature", copy=False, max_width=256, max_height=256)
    of_signature_date = fields.Datetime(
        string="Signature date",
        copy=False,
        help="Date of the signature",
        compute='_compute_signature_date',
        store=True,
        readonly=False,
    )

    # ===== Currency and Pricing fields =====
    of_currency_id = fields.Many2one(
        comodel_name='res.currency', string="Currency", readonly=True, related="of_company_id.currency_id"
    )
    of_price_subtotal = fields.Monetary(
        compute='_compute_amount', string="Price subtotal", currency_field='of_currency_id', readonly=True, store=True
    )
    of_price_tax = fields.Monetary(
        compute='_compute_amount', string="Taxes", currency_field='of_currency_id', readonly=True, store=True
    )
    of_price_total = fields.Monetary(
        compute='_compute_amount', string="Price total", currency_field='of_currency_id', readonly=True, store=True
    )

    # ===== Image fields =====
    of_image_printable_ids = fields.One2many(
        comodel_name='of.image', compute='_compute_images', string="Printable images"
    )
    of_all_image_ids = fields.One2many(comodel_name='of.image', inverse_name='intervention_id', string="All images")

    # ===== Misc. fields =====
    # Alerts
    of_alert_unable = fields.Boolean(string="No operator able", compute='_compute_of_alert_unable', store=True)
    of_alert_wrong_company = fields.Boolean(string="Incoherent company", compute='_compute_of_alert_wrong_company')
    of_has_conflict_warning = fields.Boolean(
        string="Conflict Warning",
        compute='_compute_of_has_conflict_warning',
        help="Helper field, to display warning if there is a conflict",
        store=True,
    )

    # Searching
    of_gb_employee_id = fields.Many2one(
        comodel_name='hr.employee',
        compute=lambda *a, **k: {},
        search='_search_of_gb_employee_id',
        string="Operator",
        of_custom_groupby=True,
    )

    # Helpers UX, UI fields
    of_is_flexible = fields.Boolean(string="Flexible")
    of_show_update_fpos = fields.Boolean(string="Has Fiscal Position Changed", store=False)

    # Reports fields
    of_attach_report = fields.Boolean(related='of_template_id.attach_report')
    of_report_send_date = fields.Datetime(string="Report dispatch date")

    @api.constrains('of_alert_unable')
    def _check_of_alert_unable(self):
        for event in self:
            if event.of_type == 'intervention' and event.of_alert_unable:
                raise ValidationError(_("No operator can perform this task."))

    @api.constrains('of_has_conflict_warning', 'of_force_dates')
    def _check_of_has_conflict_warning(self):
        event_obj = self.env['calendar.event']
        for event in self:
            if event.of_has_conflict_warning and not event.of_force_dates:
                if event.of_employee_ids and event.start and event.stop:
                    for employee in event.of_employee_ids:
                        if conflicts := event_obj.search(
                            [
                                ('of_employee_ids', 'in', employee.ids),
                                ('start', '<', event.stop),
                                ('stop', '>', event.start),
                                ('id', '!=', event.id),
                                ('of_state', '!=', 'cancel'),
                            ],
                            limit=1,
                        ):
                            message = _(
                                "Employee %(employee)s has at least another intervention on this time slot:"
                                "\n %(start)s: %(partner)s %(zip)s"
                            ) % {
                                'employee': employee.name,
                                'start': conflicts.start,
                                'partner': conflicts.of_partner_id.name if conflicts.of_partner_id else _('No partner'),
                                'zip': conflicts.of_address_id.zip if conflicts.of_address_id else '',
                            }
                            raise ValidationError(message)
                raise ValidationError(_("Warning, this intervention is in conflict with another one."))

    # --------------------------------------------------------------------------
    # Default methods
    # --------------------------------------------------------------------------

    def _default_of_warehouse_id(self):
        # On va récupérer le premier entrepôt de la liste
        return self.env['stock.warehouse'].search([], limit=1)

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------
    @api.depends('of_resource_id')
    def _compute_of_employee_ids(self):
        """Compute the employee_id based on the resource_id.
        In case of we are assigning an event to a resource or moving an event from one resource to another one from
        planning view, we need to update the employee_id based on the resource_id.

        Note: This method can be called by `_compute_partner_ids` (in `of_planning/models/calendar_event.py`)
            because of the `mapped('of_employee_ids.related_contact_ids')` in compute method.
            Odoo need to compute `of_employee_ids`.
        """
        for event in self:
            if event.of_employee_id:
                event.of_employee_ids -= event.of_employee_id
            if event.of_resource_id:
                event.of_employee_ids |= event.of_resource_id.employee_id
                event.of_employee_id = event.of_resource_id.employee_id
            if not event.of_employee_id:
                event.of_employee_id = event.of_employee_ids[:1]

    @api.depends('of_employee_ids', 'of_employee_id')
    def _compute_of_resource_id(self):
        for event in self:
            event.of_resource_id = (
                event.of_employee_id.resource_id
                if event.of_employee_id
                else (event.of_employee_ids and event.of_employee_ids[:1].resource_id or False)
            )

    @api.depends('allday', 'start', 'stop')
    def _compute_dates(self):
        """Override to always compute simple dates for interventions"""
        events = self.filtered(lambda e: e.of_type == 'intervention')
        for event in events:
            if event.start:
                event.start_date = event.start.date()
            if event.stop:
                event.stop_date = event.stop.date()
        return super(CalendarEvent, self - events)._compute_dates()

    @api.depends('of_partner_id', 'user_id')
    def _compute_of_company_id(self):
        for event in self:
            company_choice = self.env.user.company_id.of_company_choice or 'contact'  # 'user' or 'contact'
            company = (
                self.env.user.company_id
                if company_choice == 'user'
                else event.of_partner_id.company_id or event.user_id.company_id
            )
            event.of_company_id = company or False

    @api.depends('of_partner_id')
    def _compute_of_address_id(self):
        for event in self:
            event.of_address_id = event.of_partner_id

    @api.depends('of_employee_ids')
    def _compute_partner_ids(self):
        for event in self:
            event.partner_ids = event.mapped('of_employee_ids.related_contact_ids').filtered(
                lambda c: c.type == 'contact'
            )

    @api.depends('of_employee_ids', 'of_task_id')
    def _compute_of_alert_unable(self):
        for event in self:
            event.of_alert_unable = (
                event.of_task_id and event.of_employee_ids and not event.of_employee_ids.is_able(event.of_task_id)
            )

    @api.depends('of_employee_ids', 'of_company_id')
    def _compute_of_alert_wrong_company(self):
        for event in self:
            event.of_alert_wrong_company = bool(
                event.of_company_id
                and event.of_employee_ids.filtered(
                    lambda emp: emp.user_id and event.of_company_id not in emp.user_id.company_ids
                )
            )

    @api.depends('of_state', 'of_template_id', 'of_company_id', 'of_link_order')
    def _compute_of_fiscal_position_id(self):
        events = self.filtered(lambda e: e.of_state in ['draft', 'confirmed'] and e.of_template_id)
        for event in events:
            template_accounting = event.of_template_id.sudo()
            # Change the tax position to that of the template if it is not on the same accounting company
            # as the intervention, or if there is none AND there is no link to an order.
            change_fiscal_pos = False
            if event.of_fiscal_position_id:
                comp_accounting_company = getattr(event.of_company_id, 'accounting_company_id', event.of_company_id)
                fiscal_accounting_company = getattr(
                    event.of_fiscal_position_id.company_id,
                    'accounting_company_id',
                    event.of_fiscal_position_id.company_id,
                )
                if comp_accounting_company != fiscal_accounting_company:
                    change_fiscal_pos = True
            if (template_accounting.fiscal_position_id and not event.of_link_order) or change_fiscal_pos:
                event.of_fiscal_position_id = template_accounting.fiscal_position_id

            event._recompute_taxes()

    @api.depends('of_line_ids', 'of_line_ids.order_line_id')
    def _compute_of_link_order(self):
        for event in self.filtered('of_line_ids.order_line_id'):
            event.of_link_order = True

    @api.depends('of_template_id')
    def _compute_of_task_id(self):
        for event in self.filtered(
            lambda e: e.of_state in ['draft', 'confirmed'] and e.of_template_id and e.of_template_id.task_id
        ):
            event.of_task_id = event.of_template_id.task_id

    @api.depends('of_template_id')
    def _compute_of_line_ids(self):
        for event in self.filtered(lambda e: e.of_template_id):
            if (
                lines_to_create := [
                    Command.create(line._prepare_intervention_line_vals(event))
                    for line in event.of_template_id.line_ids
                ]
            ) and event.of_state == 'draft':
                event.of_line_ids = [Command.clear()] + lines_to_create[:]
        for event in self:
            event._recompute_taxes()

    @api.depends(
        'of_line_ids',
        'of_line_ids.price_subtotal',
        'of_line_ids.price_tax',
        'of_line_ids.price_total',
    )
    def _compute_amount(self):
        for event in self:
            event.of_price_subtotal = sum(event.mapped('of_line_ids.price_subtotal'))
            event.of_price_tax = sum(tax['amount'] for tax in event._get_taxes_values().values())
            event.of_price_total = event.of_price_subtotal + event.of_price_tax

    @api.depends('of_line_ids', 'of_line_ids.invoice_line_ids', 'of_order_id', 'of_order_id.invoice_ids')
    def _compute_invoice_ids(self):
        for event in self:
            invoices = event.of_line_ids.sudo().mapped('invoice_line_ids').mapped('move_id')
            if event.of_order_id:
                for invoice in event.of_order_id.sudo().invoice_ids:
                    invoices |= invoice
            event.of_invoice_count = len(invoices)
            event.of_invoice_ids = invoices

    @api.depends('of_order_id')
    def _compute_of_picking_domain(self):
        for event in self:
            picking_list = []
            if event.of_order_id:
                picking_list = event.of_order_id.sudo().picking_ids.ids
            event.of_picking_domain = picking_list

    @api.depends('of_state', 'of_line_ids.invoice_status')
    def _compute_of_invoice_status(self):
        """
        Compute the invoice status for the calendar event.

        The invoice status is determined based on the state of the event and the invoice status of its intervention
        lines.
        If the event is not in the states 'confirmed', 'ongoing', or 'done', the invoice status is set to 'no'.
        If any of the intervention lines have an invoice status of 'to invoice', the event invoice status is set to
        'to invoice'.
        If all intervention lines have an invoice status of 'invoiced', the event invoice status is set to 'invoiced'.
        Otherwise, the event invoice status is set to 'no'.
        """
        unconfirmed_events = self.filtered(lambda e: e.of_state not in ('confirmed', 'ongoing', 'done'))
        unconfirmed_events.of_invoice_status = 'no'
        confirmed_events = self - unconfirmed_events
        if not confirmed_events:
            return

        # Get the deposit product and category to avoid to take into account deposit lines
        deposit_product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        deposit_category_id = self.env['ir.config_parameter'].sudo().get_param('of.sale.of_deposit_product_categ_id')
        deposit_product_id = deposit_product_id and int(deposit_product_id) or False
        deposit_category_id = deposit_category_id and int(deposit_category_id) or False

        # Get the invoice status of the intervention lines that are not deposit lines
        line_invoice_status_all = [
            (d['intervention_id'][0], d['invoice_status'])
            for d in self.env['of.planning.intervention.line'].read_group(
                [
                    ('intervention_id', 'in', confirmed_events.ids),
                    ('product_id.categ_id', '!=', deposit_category_id),
                    ('product_id', '!=', deposit_product_id),
                ],
                ['intervention_id', 'invoice_status'],
                ['intervention_id', 'invoice_status'],
                lazy=False,
            )
        ]

        for event in confirmed_events:
            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == event.id]
            if event.of_state not in ('confirmed', 'ongoing', 'done'):
                event.of_invoice_status = 'no'
            elif 'to invoice' in line_invoice_status:
                event.of_invoice_status = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                event.of_invoice_status = 'invoiced'
            else:
                event.of_invoice_status = 'no'

    @api.depends('of_line_ids', 'of_line_ids.move_ids')
    def _compute_pickings(self):
        for event in self:
            event.of_picking_ids = event.of_line_ids and event.mapped('of_line_ids.move_ids.picking_id.id') or []
            event.of_delivery_count = len(event.of_picking_ids)

    @api.depends('of_partner_id', 'of_address_id')
    def _compute_of_history_intervention_ids(self):
        for event in self:
            if event.of_address_id:
                interventions = event.of_address_id.of_intervention_address_ids
            elif event.of_partner_id:
                interventions = event.of_partner_id.of_intervention_partner_ids
            else:
                interventions = self.env['calendar.event']
            event.of_history_intervention_ids = interventions.filtered(lambda i: event.start > i.start)

    @api.depends('of_order_id')
    def _compute_order_amounts(self):
        for event in self.sudo():  # bypass access rights and compute the amounts
            if event.of_order_id:
                event.of_order_amount_total = event.of_order_id.amount_total
            else:
                event.of_order_amount_total = 0.0
            event.of_order_still_due = 0.0

    @api.depends('of_picking_manual_ids')
    def _compute_picking_amounts(self):
        for event in self:
            event.of_picking_amount_total = (
                event.of_picking_manual_ids.sudo()._get_delivery_slip_value() if event.of_picking_manual_ids else 0
            )

    @api.depends('of_address_id')
    def _compute_of_previous_minutes(self):
        # used sudo to avoid access rights issues when accessing of_intervention_ids from of_address_id field
        # by a user who does not have access to all interventions (e.g : the customer was in a different company)
        for event in self.sudo():
            if event.of_address_id:
                events = (
                    event.mapped('of_address_id.of_intervention_ids')
                    .filtered(lambda e: e.start < event.start)
                    .sorted('start')
                )
                if events:
                    event.of_previous_minutes = events[-1].of_minutes

    @api.depends('of_real_start', 'of_real_stop')
    def _compute_of_total_duration(self):
        for event in self:
            if event.of_real_start and event.of_real_stop:
                duration = event.of_real_stop - event.of_real_start
                event.of_total_duration = duration.total_seconds() / 3600.0
            elif event.of_real_start:
                duration = fields.Datetime.now() - event.of_real_start
                event.of_total_duration = duration.total_seconds() / 3600.0
            else:
                event.of_total_duration = 0.0

    @api.depends('of_break_start')
    def _compute_of_in_break(self):
        for event in self:
            event.of_in_break = bool(event.of_break_start)

    @api.depends('of_real_start', 'of_real_stop', 'of_break_duration', 'of_break_start')
    def _compute_of_real_duration(self):
        for event in self:
            if not event.of_real_start and not event.of_real_stop:
                event.of_real_duration = 0.0
                continue

            if event.of_real_start:
                if event.of_real_stop:
                    duration = event.of_real_stop - event.of_real_start
                elif event.of_break_start:
                    duration = event.of_break_start - event.of_real_start
                else:
                    duration = fields.Datetime.now() - event.of_real_start
                event.of_real_duration = duration.total_seconds() / 3600.0 - event.of_break_duration

    @api.depends('of_operator_signature', 'of_customer_signature')
    def _compute_signature_date(self):
        for event in self:
            if not event.of_signature_date and (event.of_operator_signature or event.of_customer_signature):
                event.of_signature_date = fields.Datetime.now()

    @api.depends('of_all_image_ids')
    def _compute_images(self):
        for event in self:
            event.of_image_printable_ids = event.of_all_image_ids.filtered(lambda image: image.printable)

    @api.depends('start', 'stop', 'of_employee_ids', 'of_task_id')
    def _compute_of_has_conflict_warning(self):
        event_obj = self.env['calendar.event']
        for event in self:
            if event.of_employee_ids and event.start and event.stop:
                conflicts_domain = [
                    ('of_employee_ids', 'in', event.of_employee_ids.ids),
                    ('start', '<', event.stop),
                    ('stop', '>', event.start),
                    ('of_state', '!=', 'cancel'),
                ]
                if not isinstance(event.id, models.NewId):
                    conflicts_domain.append(('id', '!=', event.id))
                conflicts = event_obj.search(conflicts_domain, limit=1)
                event.of_has_conflict_warning = bool(conflicts)
            else:
                event.of_has_conflict_warning = False

    def _search_of_gb_employee_id(self, operator, value):
        return [('of_employee_ids', operator, value)]

    # --------------------------------------------------------------------------
    # Onchange methods
    # --------------------------------------------------------------------------

    @api.onchange('of_employee_ids')
    def _onchange_of_employee_ids(self):
        for event in self:
            if event.of_employee_id and event.of_employee_id.id not in event.of_employee_ids.ids:
                event.of_employee_id = False
            else:
                self._compute_of_employee_ids()

    @api.onchange('of_task_id')
    def _onchange_of_task_id(self):
        self.duration = self.of_task_id.duration

    @api.onchange('of_team_id')
    def onchange_of_team_id(self):
        self.of_employee_ids = self.of_team_id.employee_ids
        self._compute_of_employee_ids()

    @api.onchange('of_order_id')
    def _onchange_of_order_id(self):
        if self.of_order_id:
            if self.of_order_id.picking_ids:
                self.of_picking_manual_ids += self.of_order_id.picking_ids
        elif self._origin.of_order_id:
            if self._origin.of_order_id.picking_ids:
                for picking in self._origin.of_order_id.picking_ids:
                    self.of_picking_manual_ids = [Command.unlink(picking.id)]

    @api.onchange('of_fiscal_position_id')
    def _onchange_fpos_id_show_update_fpos(self):
        if self.of_line_ids and (
            not self.of_fiscal_position_id or self._origin.of_fiscal_position_id != self.of_fiscal_position_id
        ):
            self.of_show_update_fpos = True

    @api.onchange('of_type')
    def _onchange_date(self):
        """Override to not update the start_date and stop_date fields"""
        events = self.filtered(lambda e: e.of_type == 'intervention')
        return super(CalendarEvent, self - events)._onchange_date()

    @api.onchange('of_partner_id')
    def _onchange_partner_id_warning(self):
        if not (partner := self.of_partner_id):
            return
        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        if not partner.of_is_intervention_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_intervention_warn and partner.invoice_warn != 'no-message':
            if partner.invoice_warn != 'block' and partner.parent_id and partner.parent_id.invoice_warn == 'block':
                partner = partner.parent_id
            warning = {'title': _("Warning for %s") % partner.name, 'message': partner.invoice_warn_msg}
            if partner.invoice_warn == 'block':
                self.of_partner_id = False
            return {'warning': warning}

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # EXTENDS models
        return name == 'of_custom_groupby' or super()._valid_field_parameter(field, name)

    @api.model_create_multi
    def create(self, vals_list):
        task_obj = self.env['of.planning.task']
        partner_obj = self.env['res.partner']

        # Get the name of the task and the partner
        task_name_by_id = {
            task.id: task.name
            for task in task_obj.browse(vals['of_task_id'] for vals in vals_list if vals.get('of_task_id'))
        }
        partner_name_by_id = {
            partner.id: partner.name
            for partner in partner_obj.browse(vals['of_partner_id'] for vals in vals_list if vals.get('of_partner_id'))
        }

        for vals in vals_list:
            if not vals.get('name') and vals.get('of_type') == 'event':
                # in case of api creation, we need to set the name, its a required field on view
                vals['name'] = _("Event without name")
            elif not vals.get('name') and vals.get('of_type') == 'intervention':
                task_name = task_name_by_id.get(vals.get('of_task_id')) if vals.get('of_task_id') else False
                partner_name = partner_name_by_id.get(vals.get('of_partner_id')) if vals.get('of_partner_id') else False
                vals['name'] = (partner_name or '') + (partner_name and task_name and " - " or "") + (task_name or '')
        events = super().create(vals_list)
        events.filtered(lambda e: e.of_type == 'intervention')._affect_intervention_number()
        return events

    def read(self, fields=None, load='_classic_read'):
        """Override to allow access to interventions with a specific context"""
        if not self.env.is_admin() and self.env.context.get('of_force_read'):
            return super(CalendarEvent, self.sudo()).read(fields, load)
        return super().read(fields, load)

    def write(self, vals):
        res = super().write(vals)
        if 'of_line_ids' in vals:
            for intervention in self.filtered(
                lambda i: i.of_type == 'intervention'
                and i.of_state in ['confirmed', 'done']
                and i._need_for_new_picking()
            ):
                intervention.action_generate_stock_picking()
        return res

    def check_access_rule(self, operation):
        """Override to allow access to interventions with a specific context"""
        if not self.env.is_admin() and operation == 'read' and self.env.context.get('of_force_read'):
            return super(CalendarEvent, self.sudo()).check_access_rule(operation)
        return super().check_access_rule(operation)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override to make `of_type` non-searchable.
        Since we are using `calendar.event` as a model for both events and interventions, we need to make sure that
        the `of_type` field is not searchable.

        Its a technical field that should not be used in custom searches, and it is not relevant to the user.
        """
        res = super().fields_get(allfields, attributes=attributes)
        for field in res:
            if field != 'of_type':
                continue
            res[field]['searchable'] = False
        return res

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'of_gb_employee_id':
            return super()._read_group_process_groupby(gb, query)

        alias = query.left_join(self._table, 'id', 'of_employee_intervention_rel', 'intervention_id', 'of_employee_ids')

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': f'"{alias}".employee_id',
        }

    # --------------------------------------------------------------------------
    # Actions methods
    # --------------------------------------------------------------------------

    def action_button_confirm(self):
        if self._need_for_new_picking():
            self.action_generate_stock_picking()
        self.write({'of_state': 'confirmed'})

    def action_button_ongoing(self):
        self.write({'of_state': 'ongoing'})

    def action_button_done(self):
        self.action_attach_reports()
        # Avoid writing on records that are already done
        if events_not_done := self.filtered(lambda e: e.of_state != 'done'):
            events_not_done.with_context(of_from_button=True).write({'of_state': 'done'})
        self.action_send_reports_auto_done()

    def action_button_unfinished(self):
        self.write({'of_state': 'unfinished'})

    def action_button_postponed(self):
        self.write({'of_state': 'postponed'})

    def action_button_cancel(self):
        self.write({'of_state': 'cancel'})
        self.cancel_deliveries()

    def action_button_draft(self):
        self.write({'of_state': 'draft'})

    def action_button_close(self):
        self.write({'of_is_closed': True})

    def action_button_open(self):
        self.write({'of_is_closed': False})

    def action_button_send_email(self):
        self.ensure_one()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model='calendar.event',
            default_res_id=self.id,
            default_composition_mode='comment',
        )
        if template_id := self.env.ref(
            'of_planning.email_template_of_planning_intervention_report', raise_if_not_found=False
        ):
            ctx['default_template_id'] = template_id.id
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_attach_reports(self):
        """
        Attach reports to the intervention if needed.

        This method generates a PDF report for each event in the current selection and attaches it to the intervention
        as a binary attachment.

        Returns:
            None
        """
        for event in self:
            if event.of_attach_report:
                pdf, extension = self.env['ir.actions.report']._render_qweb_pdf(
                    'of_planning.report_intervention_report', res_ids=event.ids
                )

                self.env['ir.attachment'].sudo().create(
                    {
                        'name': _("Intervention Report"),
                        'type': 'binary',
                        'datas': base64.b64encode(pdf),
                        'mimetype': 'application/pdf',
                        'res_model': 'calendar.event',
                        'res_id': event.id,
                    }
                )

    def action_send_reports_auto_done(self):
        """
        Sends reports for events with 'auto_done' send_reports option.
        This method filters the events based on the 'send_reports' option of the associated template.

        Returns:
            None
        """
        if events_report_auto := self.filtered(
            lambda e: e.of_template_id and e.of_template_id.send_reports == 'auto_done'
        ):
            events_report_auto.action_send_reports_by_email()

    def action_send_reports_by_email(self):
        for event in self:
            try:
                email_template = self.env.ref('of_planning.email_template_of_planning_intervention_report')
            except Exception as e:
                raise AccessError(_("Unable to find email template")) from e

            if self.env.user.email:
                email_template = self.env.ref(
                    'of_planning.email_template_of_planning_intervention_report'
                ).with_context(default_email_from=self.env.user.email_formatted)
                email_template.with_context(force_attachment=True).send_mail(event.id, force_send=True)
                event.of_report_send_date = fields.Datetime.now()

    def action_button_import_order_line(self):
        self.ensure_one()
        line_obj = self.env['of.planning.intervention.line']
        if not self.of_order_id:
            raise UserError(_("There is no order linked to the intervention."))

        self.of_fiscal_position_id = self.of_order_id.fiscal_position_id
        existing_line_ids = self.of_line_ids.mapped('order_line_id').ids
        for line in self.of_order_id.order_line.filtered(lambda li: li.id not in existing_line_ids):
            qty = line.product_uom_qty - sum(
                line.of_intervention_line_ids.filtered(
                    lambda r: r.intervention_id.state not in ('cancel', 'postponed')
                ).mapped('qty')
            )
            if qty > 0.0:
                line_obj.create(
                    {
                        'order_line_id': line.id,
                        'intervention_id': self.id,
                        'product_id': line.product_id.id,
                        'qty': qty,
                        'price_unit': line.price_unit,
                        'name': line.name,
                        'tax_ids': [(Command.link(tax.id)) for tax in line.tax_id],
                    }
                )

    def action_button_update_lines(self):
        self.ensure_one()
        self.of_line_ids._update_vals()

    def action_button_view_invoice(self):
        invoices = self.mapped('of_invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_button_view_delivery(self):
        pickings = self.mapped('of_picking_ids')
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    def action_button_geolocalize(self):
        self.ensure_one()
        self.of_address_id.geo_localize()

    def action_button_update_taxes(self):
        self.ensure_one()

        self._recompute_taxes()

        self.message_post(
            body=_(
                "Product taxes have been recomputed according to fiscal position %s.",
                self.of_fiscal_position_id._get_html_link() if self.of_fiscal_position_id else "",
            )
        )

    def action_generate_stock_picking(self):
        if not self.of_address_id:
            raise UserError(_("A customer address is required to generate a stock picking."))
        lines = self.mapped('of_line_ids')
        if not self._need_for_new_picking():
            if len(self) == 1:
                raise UserError(_("No product to deliver in the intervention."))
            raise UserError(_("No product to deliver in the selected interventions."))
        lines.with_context(check_state=False).sudo()._action_launch_stock_rule()

    def action_create_invoice(self, view_mode='form'):
        """
        Create an invoice for the calendar event.

        This is called from an ir.actions.server, so it must return a popup wizard.

        Its creates an invoice for the calendar event based on certain conditions and data.
        It checks if a fiscal position is selected, and if not, raises a validation error.
        It also checks if the invoiceable lines are linked to order lines, and if so, it raises a message
        suggesting to do the invoicing from the sale order.
        Finally, it prepares the invoice data, creates the invoice, and posts a message on the invoice with a link
        to the calendar event.

        Returns:
            of.popup.wizard: The popup wizard with a message containing any relevant information or errors.
        """
        if len(self) > 1:  # if method is called from a recordset of many records, we force view_mode to be 'tree'
            view_mode = 'tree'

        messages_by_events = {key: {'success': [], 'error': []} for key in self}
        for event in self:
            if not event.of_fiscal_position_id:
                messages_by_events[event]['error'].append(
                    _("Intervention is non billable, please select a fiscal position.")
                )
                continue

            # All lines are linked to order lines so they should be invoiced from the sale order
            if event.of_link_order and not event.of_line_ids.filtered(lambda li: not li.order_line_id):
                messages_by_events[event]['error'].append(
                    _("Invoiceable lines are linked to order lines. Please do the invoicing from the sale order.")
                )
                continue
            if event.of_state not in ['confirmed', 'ongoing', 'done', 'unfinished', 'postponed']:
                messages_by_events[event]['error'].append(
                    _("Intervention is non billable because it must be confirmed.")
                )

            # Prepare the invoice data
            invoice_data, messages = event._prepare_invoice()
            messages_by_events[event]['error'].extend(messages)
            if not messages_by_events[event]['error'] and invoice_data:
                move_obj = self.env['account.move']
                move = move_obj.create(invoice_data)
                move.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': move, 'origin': event},
                    subtype_id=self.env.ref('mail.mt_note').id,
                )
                messages_by_events[event]['success'].append(_("Invoice created successfully."))
        if view_mode == 'form':
            if error_messages := messages_by_events[event]['error']:
                html_content_error = "<ul>" + "".join([f"<li>{msg}</li>" for msg in error_messages]) + "</ul>"
                html_message = _("<p>Invoicing could not be completed because:<br/>%s<p>") % html_content_error
            else:
                html_message = messages_by_events[event]['success'][0]
        else:
            html_message = self._format_invoice_messages_html(messages_by_events)
        return self.env['of.popup.wizard'].popup_return(message_html=html_message)

    def _need_for_new_picking(self):
        move_obj = self.env['stock.move']
        for line in self.of_line_ids:
            if line.product_id.type == 'service':
                continue
            move_lines = move_obj.search([('of_intervention_line_id', '=', line.id), ('state', '!=', 'cancel')])
            if not move_lines:
                return True
            for move_line in move_lines:
                if line.product_id != move_line.product_id or line.qty != move_line.product_uom_qty:
                    return True
        return False

    def _format_invoice_messages_html(self, messages_by_events):
        """
        Formats the invoice messages as HTML to display in the popup wizard.

        Args:
            messages_by_events (dict): A dictionary containing messages for each event.

        Returns:
            str: The formatted HTML content of the invoice messages.
        """
        has_success_message = any(messages_by_events[event]['success'] for event in self)
        has_error_message = any(messages_by_events[event]['error'] for event in self)
        html_content_success = self._build_event_details_message(messages_by_events, 'success')
        html_content_error = self._build_event_details_message(messages_by_events, 'error')
        html_message_success = (
            _("<p><strong>Invoicing completed successfully for the following interventions:</strong><br/>%s</p>")
            % html_content_success
        )
        html_message_error = (
            _("<p><strong>Invoicing could not be completed because:</strong><br/>%s<p>") % html_content_error
        )
        result = ""
        if has_success_message:
            result += f"<p>{html_message_success}</p>"
        if has_error_message:
            result += f"<p>{html_message_error}</p>"
        return result

    def _build_event_details_message(self, messages_by_events, message_type):
        """
        Builds the event details message of error or success messages as an HTML unordered list.

        Args:
            messages_by_events (dict): A dictionary containing events as keys and a list of messages as values.
            message_type (str): The type of message to format.

        Returns:
            str: The detail message as an HTML unordered list.
        """
        result = "<ul>"
        for event, messages in messages_by_events.items():
            if messages[message_type]:
                result += f"<li>{event.name}"
                if message_type == 'error':
                    msg_details = "<ul>" + "".join([f"<li>{msg}</li>" for msg in messages[message_type]]) + "</ul>"
                    result += f":<br/>{msg_details}</li>"  # noqa
        result += "</ul>"
        return result

    def action_create_invoice_list(self):
        return self.action_create_invoice(view_mode='tree')

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _affect_intervention_number(self):
        events = self.filtered(
            lambda e: e.of_state in ['confirmed', 'ongoing', 'done', 'unfinished', 'postponed'] and not e.of_number
        )
        for event in events.filtered(lambda e: e.of_template_id and e.of_template_id.sequence_id):
            event.write({'of_number': event.of_template_id.sequence_id.next_by_id()})

    def _get_invoicing_company(self, partner):
        return self.of_company_id or partner.company_id

    def _prepare_invoice_lines(self):
        """
        Prepare invoice lines for the calendar event.

        Returns:
            tuple: A tuple containing the lines data and error message.
                The lines data is a list of tuples representing the invoice lines.
                The error message is a string containing any error messages encountered during preparation.
        """
        self.ensure_one()
        line_messages = []
        lines_data = []
        for line in self.of_line_ids.filtered(lambda li: li.invoice_status == 'to invoice' and not li.order_line_id):
            line_data, messages = line._prepare_invoice_line()
            lines_data.append(Command.create(line_data))
            if messages:
                line_messages.extend(messages)
        return lines_data, line_messages

    def _prepare_invoice(self):
        """
        Prepare the data for creating an invoice from the intervention.

        Returns:
            tuple: A tuple containing the invoice data and a success message.
                    If there is an error, it returns a tuple containing False and an error message.
        """
        self.ensure_one()
        messages = []
        invoice_data = {}

        # Get the partner
        partner = self.partner_id
        partner = False
        if not partner:
            if not self.of_address_id:
                messages.append(_("No partner defined."))
                return invoice_data, messages

            invoice_address_id = (
                self.of_address_id.parent_id.address_get(['invoice'])['invoice']
                if self.of_address_id.parent_id
                else self.of_address_id.address_get(['invoice'])['invoice']
            )
            partner = self.env['res.partner'].browse(invoice_address_id)

        # Get the pricelist and the company from the partner
        pricelist = partner.property_product_pricelist
        company = self._get_invoicing_company(partner)

        fiscal_position_id = self.of_fiscal_position_id.id
        if not fiscal_position_id:
            messages.append(_("Please define a fiscal position"))
            return invoice_data, messages

        journal = self.env['account.journal'].search(
            [('company_id', '=', company.id), ('type', 'in', ['sale'])], limit=1
        )
        if not journal:
            messages.append(_("You need to define a sales journal for this company (%s).") % company.name)
            return invoice_data, messages

        # Get the invoice lines data
        lines_data, line_messages = self._prepare_invoice_lines()
        if line_messages:
            messages.extend(line_messages)
        if not lines_data:
            messages.append(_("There is no billing line present in the intervention."))

        # Get invoice data
        invoice_data |= {
            'invoice_origin': self.of_number or "Intervention",
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'partner_shipping_id': self.of_address_id.id,
            'journal_id': journal.id,
            'currency_id': pricelist.currency_id.id,
            'fiscal_position_id': fiscal_position_id,
            'company_id': company.id,
            'user_id': self._uid,
            'invoice_line_ids': lines_data,
        }
        return invoice_data, messages

    def _recompute_taxes(self):
        self.ensure_one()
        self.of_line_ids._compute_tax_ids()
        self.of_show_update_fpos = False

    def _get_taxes_values(self):
        """
        Compute the taxes for the event's line items and return the grouped tax values.

        :return: dict: A dictionary containing the grouped tax values, where the keys are account IDs and the values
        are dictionaries with 'tax_id', 'amount', and 'base' keys representing the tax ID, tax amount,
        and tax base amount respectively.
        """
        self.ensure_one()
        tax_grouped = {}
        round_curr = self.of_currency_id.round
        for line in self.of_line_ids.filtered(lambda li: li.tax_ids):
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_ids.compute_all(
                price_unit, self.of_currency_id, line.qty, product=line.product_id, partner=self.of_address_id
            )['taxes']
            for val in taxes:
                key = val['account_id']

                val['amount'] += val['base'] - round_curr(val['base'])
                if key not in tax_grouped:
                    tax_grouped[key] = {'tax_id': val['id'], 'amount': val['amount'], 'base': round_curr(val['base'])}
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])

        for values in tax_grouped.values():
            values['base'] = round_curr(values['base'])
            values['amount'] = round_curr(values['amount'])
        return tax_grouped

    def _get_calendar_event_action_views(self, action):
        """Helper method to add the tree in first position view to the given action.
        :return: dict with the updated action
        """
        event_count = len(self)
        if event_count == 1:
            views = [(self.env.ref('calendar.view_calendar_event_form', raise_if_not_found=False).id, 'form')]
            views.extend(view for view in action['views'] if view[1] != 'form')
            action['views'] = views
            return action
        else:
            if tree_view := self.env.ref('calendar.view_calendar_event_tree', raise_if_not_found=False):
                views = [(tree_view.id, 'tree')]
                views.extend(view for view in action['views'] if view[1] != 'tree')
                action['views'] = views
        return action

    def pickings_layouted(self):
        pickings = self.mapped('of_picking_manual_ids') + self.mapped('of_picking_ids')
        return [
            {
                'name': picking.name,
                'lines': picking.move_line_ids,
            }
            for picking in pickings
            if picking.move_line_ids
        ]

    def _report_get_template(self):
        """Helper method to get the intervention template to use for the report."""
        return (
            self.of_template_id
            or self.env.ref('of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
            or self.of_template_id
        )

    def _report_should_display_minutes_report(self):
        """Helper method to know if the minutes should be displayed in the report.

        :return: True if the minutes should be displayed in the report, False otherwise.
        """
        if not self:
            return False

        self.ensure_one()
        template = self._report_get_template()
        return bool(
            template.report_minutes
            and (
                (template.report_minutes_real_dates and (self.of_real_start or self.of_real_stop))
                or (template.report_minutes_real_duration and self.of_real_duration)
                or (template.report_minutes_description and self.of_minutes)
            )
        )

    def _report_should_display_dates_and_duration_report(self):
        """Helper method to know if the real dates and duration should be displayed in the intervention report.

        :return: True if the real dates and duration should be displayed in the report, False otherwise.
        """
        if not self:
            return False

        self.ensure_one()
        template = self._report_get_template()
        return bool(
            (template.report_minutes_real_dates and (self.of_real_start or self.of_real_stop))
            or (template.report_minutes_real_duration and self.of_real_duration)
        )

    def _report_should_display_minutes_sheet(self):
        """Helper method to know if the minutes should be displayed in the intervention sheet.

        :return: True if the minutes should be displayed in the minutes sheet, False otherwise.
        """
        if not self:
            return False

        self.ensure_one()
        template = self._report_get_template()
        return bool(
            template.sheet_minutes
            and (
                (template.sheet_minutes_real_dates and (self.of_real_start or self.of_real_stop))
                or (template.sheet_minutes_real_duration and self.of_real_duration)
                or (template.sheet_minutes_description and self.of_minutes)
            )
        )

    def _report_should_display_dates_and_duration_sheet(self):
        """Helper method to know if the real dates and duration should be displayed in the intervention sheet.

        :return: True if the real dates and duration should be displayed in the sheet, False otherwise.
        """
        if not self:
            return False

        self.ensure_one()
        template = self._report_get_template()
        return bool(
            (template.sheet_minutes_real_dates and (self.of_real_start or self.of_real_stop))
            or (template.sheet_minutes_real_duration and self.of_real_duration)
        )

    def _get_report_base_filename(self, what='report'):
        """Helper method to get the base filename for the intervention report."""
        if what == 'sheet':
            return _("Intervention Sheet - %s") % self.name

        task_name = self.of_task_id.name if self.of_task_id else ''
        partner_name = self.of_partner_id.display_name if self.of_partner_id else 'report'
        start_date = self.start.date() if self.start else ''
        return (
            task_name + (task_name and partner_name and ' - ' or '') + f'{partner_name} {start_date}'.replace('/', '-')
        ) or "report"

    def cancel_deliveries(self):
        """Cancel the stock pickings related to the calendar event."""
        for picking in self.of_picking_ids:
            picking.action_cancel()
