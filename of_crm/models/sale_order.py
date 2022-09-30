# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
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
    def _auto_init(self):
        """
        À l'installation du module :
            - les commandes avec l'ancien état 'Devis' sont passés au nouvel état 'Devis'
            - le nouveau champ 'Devis envoyé' est passé à vrai pour les commandes avec l'ancien état 'Devis envoyé'
        """
        cr = self._cr
        new_workflow = False
        new_canvasser_field = False
        if self._auto:
            cr.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = '%s' "
                "AND column_name = 'of_sent_quotation'" % self._table)
            new_workflow = not bool(cr.fetchall())

            cr.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = '%s' "
                "AND column_name = 'of_canvasser_id'" % self._table)
            new_canvasser_field = not bool(cr.fetchall())

        res = super(SaleOrder, self)._auto_init()

        if new_workflow:
            cr.execute("UPDATE %s "
                       "SET of_sent_quotation = True "
                       "WHERE state = 'sent'" % self._table)
            cr.execute("UPDATE %s "
                       "SET state = 'sent' "
                       "WHERE state = 'draft'" % self._table)

        if new_canvasser_field:
            cr.execute(
                "UPDATE %s SO "
                "SET of_canvasser_id = COALESCE(CL.of_prospecteur_id, RP.of_prospecteur_id, NULL) "
                "FROM %s SO2 "
                "INNER JOIN res_partner RP ON RP.id = SO2.partner_id "
                "LEFT JOIN crm_lead CL ON (CL.id = SO2.opportunity_id) "
                "WHERE SO.id = SO2.id" % (self._table, self._table))

        return res

    @api.model
    def _default_state(self):
        start_state = self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state')
        if start_state == 'quotation':
            return 'sent'
        else:
            return 'draft'

    of_referred_id = fields.Many2one(
        'res.partner', string=u"Apporté par", help="Nom de l'apporteur d'affaire", copy=False)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', domain="[('type', '=', 'opportunity')]", copy=False)
    campaign_id = fields.Many2one(
        'utm.campaign', 'Campaign', copy=False,
        help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, "
             "Christmas_Special")
    source_id = fields.Many2one(
        'utm.source', 'Source', copy=False,
        help="This is the source of the link Ex:Search Engine, another domain,or name of email list")
    medium_id = fields.Many2one(
        'utm.medium', 'Medium', copy=False, help="This is the method of delivery.Ex: Postcard, Email, or Banner Ad",
        oldname='channel_id')
    state = fields.Selection([
        ('draft', u'Estimation'),
        ('sent', u'Devis'),
        ('sale', u'Bon de commande'),
        ('done', u'Verrouillé'),
        ('cancel', u'Annulé'),
    ], default=_default_state)
    of_sent_quotation = fields.Boolean(string=u"Devis envoyé")
    of_canvasser_id = fields.Many2one(comodel_name='res.users', string=u"Prospecteur")
    of_crm_activity_ids = fields.One2many(
        comodel_name='of.crm.activity', inverse_name='order_id', string='Activities', copy=True,
        context={'active_test': False})
    of_activities_state = fields.Selection(selection=[
        ('in_progress', 'In progress'),
        ('late', 'Late'),
        ('done', 'Done'),
        ('canceled', 'Canceled')], string='Status of activities', compute='_compute_of_activities_state', store=True)
    # Follow-up fields
    of_sale_followup_tag_ids = fields.Many2many(
        comodel_name='of.sale.followup.tag', relation='sale_order_followup_tag_rel', column1='order_id',
        column2='tag_id', string='Follow-up tags')
    of_priority = fields.Selection(selection=AVAILABLE_PRIORITIES, string='Priority', index=True, default='0')
    of_notes = fields.Text(string='Follow-up notes')
    of_info = fields.Text(string='Info')
    of_reference_laying_date = fields.Date(
        compute='_compute_of_reference_laying_date', string='Reference laying date', store=True)
    of_force_laying_date = fields.Boolean(string='Force laying date')
    of_manual_laying_date = fields.Date(string='Manual laying date')
    of_laying_week = fields.Char(compute='_compute_of_reference_laying_date', string="Laying week", store=True)
    of_main_product_brand_id = fields.Many2one(
        comodel_name='of.product.brand', compute='_of_compute_main_product_brand_id',
        string="Brand of the main product", store=True)

    @api.multi
    @api.depends('of_force_laying_date', 'of_manual_laying_date', 'intervention_ids',
                 'intervention_ids.date', 'intervention_ids.type_id', 'intervention_ids.state')
    def _compute_of_reference_laying_date(self):
        for rec in self:
            laying_date = False
            if rec.of_force_laying_date:
                laying_date = rec.of_manual_laying_date
            elif rec.intervention_ids:
                installation_type = self.env.ref('of_service.of_service_type_installation')
                inter_installation = rec.intervention_ids.filtered(
                    lambda i: i.type_id == installation_type and i.state == 'confirm')
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
                rec.of_laying_week = u"Non programmée"

    @api.multi
    @api.depends('of_crm_activity_ids', 'of_crm_activity_ids.state', 'of_crm_activity_ids.deadline_date')
    def _compute_of_activities_state(self):
        for sale in self:
            activities = sale.of_crm_activity_ids
            if not activities:
                sale.of_activities_state = False
                continue

            activities_state = 'in_progress'
            states = activities.mapped('state')
            if all(map(lambda s: s == 'canceled', states)):
                activities_state = 'canceled'
            elif all(map(lambda s: s in ('done', 'canceled'), states)):
                activities_state = 'done'
            elif sale._of_get_overdue_activities():
                activities_state = 'late'
            sale.of_activities_state = activities_state

    @api.multi
    @api.depends(
        'order_line', 'order_line.of_article_principal', 'order_line.product_id', 'order_line.product_id.brand_id')
    def _of_compute_main_product_brand_id(self):
        for rec in self:
            main_product_lines = rec.order_line.filtered(lambda l: l.of_article_principal)
            if main_product_lines:
                rec.of_main_product_brand_id = main_product_lines[0].product_id.brand_id

    @api.multi
    def _of_update_deadline_date_activities(self, activity_fields=None):
        """Recomputes the deadline date of activities linked to the Sale.
        :param activity_fields: The list of fields that are updated to filter activities to update
        :type activity_fields: list
        """
        if activity_fields is None:
            activity_fields = []

        field_name = self._get_date_fields_mapping_order_to_activity()
        activities_filter = [field_name.get(af) for af in activity_fields if field_name.get(af)]
        for order in self:
            for crm_activity in order.of_crm_activity_ids.filtered(
                    lambda sa:
                    sa.state == 'planned' and sa.type_id and
                    sa.type_id.of_compute_date in activities_filter and
                    sa.type_id.of_automatic_recompute):
                crm_activity.deadline_date = self._of_get_sale_activity_date_deadline(
                    order, crm_activity.type_id)

    def _get_date_fields_mapping_order_to_activity(self):
        return {
            'confirmation_date': 'confirmation_date',
            'of_reference_laying_date': 'reference_install_date',
            'of_force_laying_date': 'reference_install_date',
            'of_manual_laying_date': 'reference_install_date',
            'of_date_de_pose': 'estimated_install_date',
            'of_date_vt': 'technical_visit_date'
        }

    def _get_date_fields_mapping_activity_to_order(self):
        return {
            'confirmation_date': 'confirmation_date',
            'reference_install_date': 'of_reference_laying_date',
            'estimated_install_date': 'of_date_de_pose',
            'technical_visit_date': 'of_date_vt'
        }

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        if self.partner_id.of_prospecteur_id:
            self.of_canvasser_id = self.partner_id.of_prospecteur_id

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
            if self.opportunity_id.of_prospecteur_id and self.state != 'sale':
                self.of_canvasser_id = self.opportunity_id.of_prospecteur_id

    @api.multi
    def _of_get_overdue_activities(self):
        self.ensure_one()
        return self.of_crm_activity_ids.filtered(lambda a: a.is_late)

    def _of_get_fields_recompute_auto_activities(self):
        """Helper function to return the list of fields that will trigger the recompute
        the deadline date of activities"""
        return [
            'confirmation_date', 'of_reference_laying_date', 'of_date_de_pose', 'of_date_vt', 'of_force_laying_date',
            'of_manual_laying_date']

    @api.model
    def _of_get_sale_activity_user_id(self, order, activity):
        if not order or not activity:
            return False
        if activity.of_user_assignement == 'canvasser':
            return order.of_canvasser_id.id
        elif activity.of_user_assignement == 'creator':
            return order.create_uid.id or order.env.user.id
        elif activity.of_user_assignement == 'responsible':
            return order.of_user_id.id
        elif activity.of_user_assignement == 'salesman':
            return order.user_id.id
        elif activity.of_user_assignement == 'specific_user':
            return activity.of_user_id.id
        return False

    @api.model
    def _of_get_sale_activity_date_deadline(self, order, activity, days=False, compute_date=False):
        if not order or not activity:
            return False
        if not days:
            days = activity.days
        if not compute_date:
            compute_date = activity.of_compute_date
        # dict to translate the value of the field selection into attribute's name of the model
        field_name = self._get_date_fields_mapping_activity_to_order()
        order_field = field_name.get(compute_date)
        if order_field:
            # take the manual date if required
            if order_field == 'of_reference_laying_date' and order.of_force_laying_date:
                order_field = 'of_manual_laying_date'
            ddate = getattr(order, order_field)
            ddate = fields.Date.from_string(ddate)
        else:
            ddate = fields.Date.from_string(fields.Date.today())
        if ddate:
            delta = timedelta(days=days)
            return ddate + delta
        return False

    @api.model
    def create(self, vals):
        start_state = 'draft'

        # On teste si l'utilisateur a le groupe quotation
        if self.env.user.has_group('of_crm.group_quotation_sale_order_state'):
            # Si oui, on teste si la commande ne vient pas du site web/public user
            public_partner = self.env.ref('base.public_partner')
            partner_id = self.env['res.partner'].browse(vals.get('partner_id', False))

            if partner_id == public_partner:
                # La commande vient du site web, on laisse en estimation malgré le paramétrage
                pass
            else:
                start_state = 'quotation'

        if start_state == 'quotation':
            if vals.get('state', 'draft') == 'draft':
                vals.update(state='sent')
        else:
            vals.update(state='draft')
        order = super(SaleOrder, self).create(vals)
        if vals.get('opportunity_id'):
            lead = self.env['crm.lead'].browse(vals['opportunity_id'])
            # on connecte la commande aux RDV plutôt que l'inverse car plus facile de toucher un M2O qu'un O2M
            lead.of_intervention_ids.write({'order_id': order.id})
        # activate and deactivate activities
        order.deactivate_activities_triggered_later()
        # Check if the dict of values contains fields that will trigger the recompute of the deadline date of
        # the activities.
        activity_fields = filter(
            lambda f: f, [f in self._of_get_fields_recompute_auto_activities() and f for f in vals.keys()])
        if activity_fields:
            order._of_update_deadline_date_activities(activity_fields)

        return order

    @api.multi
    def write(self, values):
        start_state = self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state')
        if values.get('state', False) == 'draft' and start_state == 'quotation':
            values.update(state='sent')
        res = super(SaleOrder, self).write(values)
        if values.get('of_crm_activity_ids'):
            self.filtered(
                lambda o: o.state not in ['sale', 'cancel', 'done']).deactivate_activities_triggered_later()
        if values.get('opportunity_id') and len(self) == 1:
            lead = self.env['crm.lead'].browse(values['opportunity_id'])
            # on connecte la commande aux RDV plutôt que l'inverse car plus facile de toucher un M2O qu'un O2M
            lead.of_intervention_ids.write({'order_id': self.id})
        return res

    @api.multi
    def _write(self, values):
        res = super(SaleOrder, self)._write(values)
        # Low level implementation to ensure that we will update the activities deadline date after the computed fields.
        # Check if the dict of values contains fields that will trigger the recompute of the deadline date of
        # the activities.
        activity_fields = filter(
            lambda f: f, [f in self._of_get_fields_recompute_auto_activities() and f for f in values.keys()])
        if activity_fields:
            self._of_update_deadline_date_activities(activity_fields)
        return res

    def _of_not_done_mandatory_activities(self):
        return self.mapped('of_crm_activity_ids').filtered(
            lambda act: act.type_id and act.type_id.of_mandatory and act.state == 'planned' and act.active
        ).mapped('title')

    @api.multi
    def action_confirm(self):
        """
        Un prospect devient signé sur confirmation de commande
        """
        mandatory_activities = self._of_not_done_mandatory_activities()
        if mandatory_activities:
            raise ValidationError(_(
                'You cannot confirm the Order until the mandatory activities are completed.\n'
                'Please check the following activities :\n%s') % (''.join(map(
                    lambda ma: ma and '- %s\n' % ma, mandatory_activities))))
        res = super(SaleOrder, self).action_confirm()
        self.update_of_customer_state()
        self.activate_activities_triggered_at_confirmation()
        return res

    @api.multi
    def update_of_customer_state(self):
        partners = self.env['res.partner']
        for order in self:
            if order.partner_id.of_customer_state == 'lead' and order.partner_id not in partners:
                partners += order.partner_id
        partners and partners.write({'of_customer_state': 'customer'})

    @api.multi
    def action_draft(self):
        res = super(SaleOrder, self).action_draft()
        self.mapped('of_crm_activity_ids').filtered(lambda a: a.state == 'canceled').action_plan()
        self.deactivate_activities_triggered_later()
        return res

    @api.multi
    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        self.mapped('of_crm_activity_ids').filtered(lambda a: a.state == 'planned').action_cancel()
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
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'of_mark_so_as_sent': True,
            'default_composition_mode': 'comment',
            'custom_layout': "sale.mail_template_data_notification_email_sale_order"
        })
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
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_canvasser_id'] = self.of_canvasser_id.id
        return invoice_vals

    @api.model
    def cron_recompute_activities_state(self):
        for order in self.search([('of_crm_activity_ids', '!=', False)]):
            order._compute_of_activities_state()

    @api.multi
    def _get_activities_to_deactivate_at_creation(self):
        return self.mapped('of_crm_activity_ids').filtered(
            lambda a: a.active and a.trigger_type and a.trigger_type != 'at_creation')

    @api.multi
    def _get_activities_to_activate_at_confirmation(self):
        return self.mapped('of_crm_activity_ids').filtered(lambda a: not a.active and a.trigger_type == 'at_validation')

    @api.multi
    def deactivate_activities_triggered_later(self):
        """Will deactivate the activities that are not in the list of activities to trigger at the creation.
        That will hide all activities that are not to do yet.
        The other activities will be activated later when the order will be confirmed for instance.
        """
        self._get_activities_to_deactivate_at_creation().write({'active': False})

    @api.multi
    def activate_activities_triggered_at_confirmation(self):
        """Will activate the activities that are in the list of activities to trigger at the confirmation.
        """
        self._get_activities_to_activate_at_confirmation().write({'active': True})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_amount_to_invoice = fields.Float(
        string=u"Reste à facturer en €", compute="_compute_of_amount_to_invoice", store=True)

    @api.depends('product_uom_qty', 'qty_invoiced', 'price_unit', 'discount')
    def _compute_of_amount_to_invoice(self):
        for line in self:
            line.of_amount_to_invoice = (line.product_uom_qty - line.qty_invoiced) * line.price_unit * \
                (1 - (line.discount or 0.0) / 100.0)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _auto_init(self):
        cr = self._cr
        new_canvasser_field = False
        if self._auto:
            cr.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = '%s' "
                "AND column_name = 'of_canvasser_id'" % self._table)
            new_canvasser_field = not bool(cr.fetchall())

        res = super(AccountInvoice, self)._auto_init()

        if new_canvasser_field:
            cr.execute(
                "UPDATE %s AI "
                "SET of_canvasser_id = COALESCE(SO.of_canvasser_id, RP.of_prospecteur_id, NULL) "
                "FROM  %s AI2 "
                "INNER JOIN res_partner RP ON RP.id = AI2.partner_id "
                "LEFT JOIN sale_order SO ON (SO.name = AI2.origin) "
                "WHERE AI.id = AI2.id" % (self._table, self._table))

        return res

    of_canvasser_id = fields.Many2one(
        comodel_name='res.users', string=u"Prospecteur", readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user)

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        self.update_of_customer_state()
        return res

    @api.multi
    def update_of_customer_state(self):
        partners = self.env['res.partner']
        for invoice in self:
            if invoice.partner_id.of_customer_state == 'lead' and invoice.partner_id not in partners and \
                    invoice.partner_id.customer:
                partners += invoice.partner_id
        partners and partners.write({'of_customer_state': 'customer'})


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def _auto_init(self):
        super(SaleConfiguration, self)._auto_init()
        if not self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state'):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_sale_order_start_state', 'quotation')

    @api.model
    def _init_sale_order_state_group(self):
        group_quotation_sale_order_state = self.env.ref('of_crm.group_quotation_sale_order_state')
        group_estimation_sale_order_state = self.env.ref('of_crm.group_estimation_sale_order_state')
        group_user = self.env.ref('base.group_user')
        if group_quotation_sale_order_state not in group_user.implied_ids and \
                group_estimation_sale_order_state not in group_user.implied_ids:
            self.env.ref('base.group_public').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})
            self.env.ref('base.group_portal').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})
            self.env.ref('base.group_user').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})

    @api.model
    def _init_crm_funnel_conversion_group(self):
        group_funnel_conversion1 = self.env.ref('of_crm.group_funnel_conversion1')
        if not self.env['ir.values'].search(
                [('name', '=', 'of_display_funnel_conversion1'), ('model', '=', 'sale.config.settings')]):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_display_funnel_conversion1', True)
            self.env.ref('sales_team.group_sale_salesman').write({'implied_ids': [(4, group_funnel_conversion1.id)]})
        group_funnel_conversion2 = self.env.ref('of_crm.group_funnel_conversion2')
        if not self.env['ir.values'].search(
                [('name', '=', 'of_display_funnel_conversion2'), ('model', '=', 'sale.config.settings')]):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_display_funnel_conversion2', True)
            self.env.ref('sales_team.group_sale_salesman').write({'implied_ids': [(4, group_funnel_conversion2.id)]})

    group_estimation_sale_order_state = fields.Boolean(
        string=u"Commandes créés à l'étape Estimation",
        implied_group='of_crm.group_estimation_sale_order_state',
        group='base.group_portal,base.group_user,base.group_public')
    group_quotation_sale_order_state = fields.Boolean(
        string=u"Commandes créés à l'étape Devis",
        implied_group='of_crm.group_quotation_sale_order_state',
        group='base.group_user')
    of_sale_order_start_state = fields.Selection(
        selection=[('estimation', u"Les commandes sont créées à l'étape initiale Estimation"),
                   ('quotation', u"Les commandes sont créées à l'étape initiale Devis")],
        string=u"(OF) État de départ des commandes",
        default='quotation',
        required=True)
    of_lost_opportunity_stage_id = fields.Many2one(
        comodel_name='crm.stage', string=u"(OF) Étape perdue des opportunités",
        help=u"Permet d'indiquer quelle est l'étape associée à la perte d'opportunité pour des besoins d'analyse")
    group_funnel_conversion1 = fields.Boolean(
        string=u"Affichage du tunnel de conversion qualitatif",
        implied_group='of_crm.group_funnel_conversion1',
        group='sales_team.group_sale_salesman')
    of_display_funnel_conversion1 = fields.Boolean(
        string=u"(OF) Affichage du tunnel de conversion qualitatif", default=True)
    group_funnel_conversion2 = fields.Boolean(
        string=u"Affichage du tunnel de conversion quantitatif",
        implied_group='of_crm.group_funnel_conversion2',
        group='sales_team.group_sale_salesman')
    of_display_funnel_conversion2 = fields.Boolean(
        string=u"(OF) Affichage du tunnel de conversion quantitatif", default=True)

    @api.multi
    def set_of_sale_order_start_state_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_sale_order_start_state', self.of_sale_order_start_state)

    @api.onchange('of_sale_order_start_state')
    def _onchange_of_sale_order_start_state(self):
        if self.of_sale_order_start_state == "estimation":
            self.update({
                'group_estimation_sale_order_state': True,
                'group_quotation_sale_order_state': False,
            })
        else:
            self.update({
                'group_estimation_sale_order_state': False,
                'group_quotation_sale_order_state': True,
            })

    @api.multi
    def set_of_lost_opportunity_stage_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_lost_opportunity_stage_id', self.of_lost_opportunity_stage_id.id)

    @api.multi
    def set_of_display_funnel_conversion1(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_display_funnel_conversion1', self.of_display_funnel_conversion1)

    @api.onchange('of_display_funnel_conversion1')
    def _onchange_of_display_funnel_conversion1(self):
        if self.of_display_funnel_conversion1:
            self.update({'group_funnel_conversion1': True})
        else:
            self.update({'group_funnel_conversion1': False})

    @api.multi
    def set_of_display_funnel_conversion2(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_display_funnel_conversion2', self.of_display_funnel_conversion2)

    @api.onchange('of_display_funnel_conversion2')
    def _onchange_of_display_funnel_conversion2(self):
        if self.of_display_funnel_conversion2:
            self.update({'group_funnel_conversion2': True})
        else:
            self.update({'group_funnel_conversion2': False})


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get('default_res_id') and \
                self._context.get('of_mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            order.of_sent_quotation = True
            self = self.with_context(mail_post_autofollow=True)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
