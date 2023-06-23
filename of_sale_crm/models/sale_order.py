# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'of.crm.stage.auto.update']

    @api.model
    def _default_state(self):
        start_state = self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state')
        if start_state == 'quotation':
            return 'sent'
        else:
            return 'draft'

    of_referred_id = fields.Many2one(
        'res.partner', string="Apporté par", help="Nom de l'apporteur d'affaire", copy=False
    )
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', domain="[('type', '=', 'opportunity')]", copy=False
    )
    campaign_id = fields.Many2one(
        'utm.campaign',
        'Campaign',
        copy=False,
        help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, "
        "Christmas_Special",
    )
    source_id = fields.Many2one(
        'utm.source',
        'Source',
        copy=False,
        help="This is the source of the link Ex:Search Engine, another domain,or name of email list",
    )
    medium_id = fields.Many2one(
        'utm.medium',
        'Medium',
        copy=False,
        help="This is the method of delivery.Ex: Postcard, Email, or Banner Ad",
        oldname='channel_id',
    )
    state = fields.Selection(
        [
            ('draft', "Estimation"),
            ('sent', "Devis"),
            ('sale', "Bon de commande"),
            ('done', "Verrouillé"),
            ('cancel', "Annulé"),
        ],
        default=_default_state,
    )
    of_sent_quotation = fields.Boolean(string="Devis envoyé", copy=False)
    of_canvasser_id = fields.Many2one(comodel_name='res.users', string="Prospecteur")
    of_crm_activity_ids = fields.One2many(
        comodel_name='of.crm.activity',
        inverse_name='order_id',
        string='Activities',
        copy=True,
        context={'active_test': False},
    )
    of_activities_state = fields.Selection(
        selection=[('in_progress', 'In progress'), ('late', 'Late'), ('done', 'Done'), ('canceled', 'Canceled')],
        string='Status of activities',
        compute='_compute_of_activities_state',
        store=True,
    )
    # Follow-up fields
    of_sale_followup_tag_ids = fields.Many2many(
        comodel_name='of.sale.followup.tag',
        relation='sale_order_followup_tag_rel',
        column1='order_id',
        column2='tag_id',
        string='Follow-up tags',
    )
    of_priority = fields.Selection(selection=AVAILABLE_PRIORITIES, string='Priority', index=True, default='0')
    of_notes = fields.Text(string='Follow-up notes')
    of_info = fields.Text(string='Info')
    of_reference_laying_date = fields.Date(
        compute='_compute_of_reference_laying_date', string='Reference laying date', store=True, compute_sudo=True
    )
    of_force_laying_date = fields.Boolean(string='Force laying date')
    of_manual_laying_date = fields.Date(string='Manual laying date')
    of_laying_week = fields.Char(
        compute='_compute_of_reference_laying_date', string="Laying week", store=True, compute_sudo=True
    )
    of_main_product_brand_id = fields.Many2one(
        comodel_name='of.product.brand',
        compute='_of_compute_main_product_brand_id',
        string="Brand of the main product",
        store=True,
    )

    @api.depends(
        'of_force_laying_date',
        'of_manual_laying_date',
        'intervention_ids',
        'intervention_ids.date',
        'intervention_ids.type_id',
        'intervention_ids.state',
    )
    def _compute_of_reference_laying_date(self):
        for rec in self:
            laying_date = False
            if rec.of_force_laying_date:
                laying_date = rec.of_manual_laying_date
            elif rec.intervention_ids:
                installation_type = self.env.ref('of_service.of_service_type_installation')
                inter_installation = rec.intervention_ids.filtered(
                    lambda i: i.type_id == installation_type and i.state in ['draft', 'confirm']
                )
                # by default Interventions are sorted by date (_order = 'date')

                if inter_installation:
                    laying_date = inter_installation[0].date_date or False
                else:
                    # we keep the old value
                    laying_date = rec.read(['of_reference_laying_date'])[0]['of_reference_laying_date']
            rec.of_reference_laying_date = laying_date
            if laying_date:
                date_laying_week = datetime.strptime(laying_date, "%Y-%m-%d").date()
                laying_week = date_laying_week.isocalendar()[1]
                rec.of_laying_week = "%s - S%02d" % (date_laying_week.year, laying_week)
            else:
                rec.of_laying_week = "Non programmée"

    @api.depends('of_crm_activity_ids', 'of_crm_activity_ids.state', 'of_crm_activity_ids.deadline_date')
    def _compute_of_activities_state(self):
        for sale in self:
            activities = sale.of_crm_activity_ids
            if not activities:
                sale.of_activities_state = False
                continue

            activities_state = 'in_progress'
            states = activities.mapped('state')
            if all(s == 'canceled' for s in states):
                activities_state = 'canceled'
            elif all(s in ('done', 'canceled') for s in states):
                activities_state = 'done'
            elif sale._of_get_overdue_activities():
                activities_state = 'late'
            sale.of_activities_state = activities_state

    @api.depends(
        'order_line', 'order_line.of_article_principal', 'order_line.product_id', 'order_line.product_id.brand_id'
    )
    def _of_compute_main_product_brand_id(self):
        for rec in self:
            main_product_lines = rec.order_line.filtered('of_article_principal')
            if main_product_lines:
                rec.of_main_product_brand_id = main_product_lines[0].product_id.brand_id

    def _of_update_deadline_date_activities(self, activity_fields):
        """Recomputes the deadline date of activities linked to the Sale.
        :param activity_fields: The list of fields that are updated to filter activities to update
        :type activity_fields: list
        """
        activities = self.env['crm.activity'].search(
            [('of_compute_date_id', 'in', activity_fields.ids), ('of_automatic_recompute', '=', True)]
        )
        for of_crm_activity in self.of_crm_activity_ids.filtered(
            lambda sa: sa.state == 'planned' and sa.type_id in activities
        ):
            of_crm_activity.deadline_date = of_crm_activity.type_id.of_compute_date_deadline(of_crm_activity.order_id)

    @api.onchange('partner_id')
    def onchange_partner_id_canvasser(self):
        if self.partner_id.of_canvasser_id:
            self.of_canvasser_id = self.partner_id.of_canvasser_id

    @api.onchange('opportunity_id')
    def onchange_opportunity(self):
        if self.opportunity_id:
            self.of_referred_id = self.opportunity_id.of_referred_id
            self.campaign_id = self.opportunity_id.campaign_id
            self.medium_id = self.opportunity_id.medium_id
            self.source_id = self.opportunity_id.source_id
            self.team_id = self.opportunity_id.team_id
            if self.opportunity_id.user_id and self.state != 'sale':
                self.user_id = self.opportunity_id.user_id
            if self.opportunity_id.of_canvasser_id and self.state != 'sale':
                self.of_canvasser_id = self.opportunity_id.of_canvasser_id

    @api.multi
    def _of_get_overdue_activities(self):
        self.ensure_one()
        return self.of_crm_activity_ids.filtered('is_late')

    def _of_get_sale_activity_user(self, activity):
        if not activity or len(self) != 1:
            return False
        if activity.of_user_assignment == 'canvasser':
            return self.of_canvasser_id
        if activity.of_user_assignment == 'creator':
            return self.create_uid or self.env.user
        if activity.of_user_assignment == 'responsible':
            return self.of_user_id
        if activity.of_user_assignment == 'salesman':
            return self.user_id
        if activity.of_user_assignment == 'specific_user':
            return activity.of_user_id
        return False

    @api.model_create_multi
    def create(self, vals_list):
        # :todo: La partie sur le state devrait être mise dans of_sale
        start_state = 'draft'
        # On teste si l'utilisateur a le groupe quotation
        if self.env.user.has_group('of_crm.group_quotation_sale_order_state'):
            if not self.env.context.get('website_order'):
                # La commande ne vient pas du site web, on peut la passer en état devis
                start_state = 'quotation'
        if start_state == 'quotation':
            for vals in vals_list:
                if vals.get('state', 'draft') == 'draft':
                    vals['state'] = 'sent'
        else:
            for vals in vals_list:
                vals['state'] = 'draft'

        orders = super().create(vals_list)

        # :todo: Vérifier la pertinence de ce code. Devrait se limiter aux interventions qui n'ont pas déjà
        #    un bon de commande associé
        for sale_order in orders:
            if sale_order.opportunity_id:
                sale_order.opportunity_id.of_intervention_ids.order_id = sale_order

        # activate and deactivate activities
        orders.deactivate_activities_triggered_later()

        # Check if the dict of values contains fields that will trigger the recompute of the deadline date of
        # the activities.
        for sale_order, vals in zip(orders, vals_list):
            activity_fields = self.env['of.crm.compute.date'].search(
                [('res_field', 'in', vals), ('res_model', '=', 'sale.order')]
            )
            if activity_fields:
                sale_order._of_update_deadline_date_activities(activity_fields)
        return orders

    @api.multi
    def write(self, values):
        start_state = self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state')
        if values.get('state', False) == 'draft' and start_state == 'quotation':
            values.update(state='sent')
        res = super().write(values)
        if values.get('of_crm_activity_ids'):
            self.filtered(lambda o: o.state not in ['sale', 'cancel', 'done']).deactivate_activities_triggered_later()
        if values.get('opportunity_id') and len(self) == 1:
            lead = self.env['crm.lead'].browse(values['opportunity_id'])
            # on connecte la commande aux RDV plutôt que l'inverse car plus facile de toucher un M2O qu'un O2M
            lead.of_intervention_ids.write({'order_id': self.id})

        activity_fields = self.env['of.crm.compute.date'].search(
            [('res_field', 'in', values), ('res_model', '=', 'sale.order')]
        )
        if activity_fields:
            self._of_update_deadline_date_activities(activity_fields)
        return res

    def _of_not_done_mandatory_activities(self):
        return self.of_crm_activity_ids.filtered(
            lambda act: act.active and act.state == 'planned' and act.type_id.of_mandatory
        ).mapped('title')

    @api.multi
    def action_confirm(self):
        """
        Un prospect devient signé sur confirmation de commande
        """
        mandatory_activities = self._of_not_done_mandatory_activities()
        if mandatory_activities:
            raise ValidationError(
                _(
                    'You cannot confirm the Order until the mandatory activities are completed.\n'
                    'Please check the following activities :\n%s'
                )
                % (''.join(['- %s\n' % ma for ma in mandatory_activities]))
            )

        res = super().action_confirm()
        self.update_of_customer_state()
        self.activate_activities_triggered_at_confirmation()
        return res

    @api.multi
    def update_of_customer_state(self):
        partners = self.partner_ids.filtered(lambda p: p.of_customer_state == 'lead')
        if partners:
            partners.of_customer_state = 'customer'

    @api.multi
    def action_draft(self):
        res = super().action_draft()
        self.of_crm_activity_ids.filtered(lambda a: a.state == 'canceled').action_plan()
        self.deactivate_activities_triggered_later()
        return res

    @api.multi
    def action_cancel(self):
        res = super().action_cancel()
        self.of_crm_activity_ids.filtered(lambda a: a.state == 'planned').action_cancel()
        return res

    @api.multi
    def action_confirm_estimation(self):
        return self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})

    @api.multi
    def print_quotation(self):
        # on redéfinit la fonction standard pour court-circuiter le changement d'état
        return self.env['report'].get_action(self, 'sale.report_saleorder')

    @api.multi
    def action_quotation_send(self):
        # on redéfinit la fonction standard pour court-circuiter le changement d'état
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update(
            {
                'default_model': 'sale.order',
                'default_res_id': self.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'of_mark_so_as_sent': True,
                'default_composition_mode': 'comment',
                'custom_layout': "sale.mail_template_data_notification_email_sale_order",
            }
        )
        mail_subtype = self.env.ref('of_base.mail_message_subtype_mail', raise_if_not_found=False)
        if mail_subtype:
            ctx['default_subtype_id'] = mail_subtype.id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['of_canvasser_id'] = self.of_canvasser_id.id
        return invoice_vals

    @api.model
    def cron_recompute_activities_state(self):
        yesterday = date.today() - timedelta(days=1)
        for order in self.search([('of_crm_activity_ids.deadline_date', '=', fields.Date.to_string(yesterday))]):
            order._compute_of_activities_state()

    @api.multi
    def _get_activities_to_deactivate_at_creation(self):
        return self.mapped('of_crm_activity_ids').filtered(
            lambda a: a.active and a.trigger_type and a.trigger_type != 'at_creation'
        )

    @api.multi
    def _get_activities_to_activate_at_confirmation(self):
        return self.mapped('of_crm_activity_ids').filtered(lambda a: not a.active and a.trigger_type == 'at_validation')

    @api.multi
    def deactivate_activities_triggered_later(self):
        """Will deactivate the activities that are not in the list of activities to trigger at the creation.
        That will hide all activities that are not to do yet.
        The other activities will be activated later when the order will be confirmed for instance.
        """
        self._get_activities_to_deactivate_at_creation().active = False

    @api.multi
    def activate_activities_triggered_at_confirmation(self):
        """Will activate the activities that are in the list of activities to trigger at the confirmation."""
        self._get_activities_to_activate_at_confirmation().active = True
