# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(selection=[
        ('draft', u"Estimation"),
        ('sent', u"Devis"),
        ('presale', u"Bon de commande"),
        ('sale', u"Commande enregistrée"),
        ('done', u"Verrouillé"),
        ('cancel', u"Annulé"),
        ('closed', u"Clôturé"),
    ])
    of_custom_confirmation_date = fields.Datetime(string=u"Date de confirmation")
    confirmation_date = fields.Datetime(string=u"Date d'enregistrement")

    @api.depends('state', 'order_line.invoice_status', 'of_force_invoice_status', 'of_cancelled_order_id',
                 'of_cancellation_order_id')
    def _get_invoiced(self):
        super(SaleOrder, self)._get_invoiced()
        for order in self:
            if order.state == 'closed':
                if order.of_cancelled_order_id or order.of_cancellation_order_id:
                    order.invoice_status = 'no'
                else:
                    order.invoice_status = 'invoiced'

    @api.multi
    def action_verification_preconfirm(self):
        """
        Permet de faire les vérification avant de démarrer la pré-confirmation de la commande.
        Comme il n'y a pas de raise si on veut une vérification qui bloque la confirmation il faut le faire hors de
        action_preconfirm, autrement certaines surcharge qui seraient passées avant/après seront tout de même réalisées
        """
        action = False
        for order in self:
            action, interrupt = self.env['of.sale.order.verification'].do_verification(order)
            if interrupt:
                return action
        res = self.action_preconfirm()
        if action:
            return action
        return res

    @api.multi
    def action_preconfirm(self):
        for order in self:
            order.state = 'presale'
            order.of_custom_confirmation_date = fields.Datetime.now()
            ir_config_obj = self.env['ir.config_parameter']
            if not self._context.get('order_cancellation', False) and \
                    not ir_config_obj.get_param('of.followup.migration', False):
                order.with_context(auto_followup=True, followup_creator_id=self.env.user.id).sudo().\
                    action_followup_project()
        self.activate_activities_triggered_at_validation()
        return True

    @api.multi
    def action_reopen(self):
        self.ensure_one()
        # On ré-ouvre le suivi
        if self.of_followup_project_id:
            self.of_followup_project_id.set_to_in_progress()
        self.state = 'sale'
        return True

    @api.multi
    def _get_activities_to_activate_at_validation(self):
        return self.mapped('of_crm_activity_ids').filtered(lambda a: not a.active and a.trigger_type == 'at_validation')

    @api.multi
    def _get_activities_to_activate_at_confirmation(self):
        return self.mapped('of_crm_activity_ids').filtered(
            lambda a: not a.active and a.trigger_type == 'at_confirmation')

    @api.multi
    def activate_activities_triggered_at_validation(self):
        """Will activate the activities that are in the list of activities to trigger at the validation.
        """
        self._get_activities_to_activate_at_validation().write({'active': True})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    confirmation_date_order = fields.Datetime(string=u"Date d'enregistrement de commande")
    of_confirmation_date = fields.Datetime(string=u"Date d'enregistrement")

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced',
                 'order_id.of_invoice_policy', 'order_id.partner_id.of_invoice_policy',
                 'order_id.of_cancelled_order_id', 'order_id.of_cancellation_order_id')
    def _compute_invoice_status(self):
        super(SaleOrderLine, self)._compute_invoice_status()
        for line in self:
            if line.state == 'closed':
                if line.order_id.of_cancelled_order_id or line.order_id.of_cancellation_order_id:
                    line.invoice_status = 'no'
                else:
                    line.invoice_status = 'invoiced'


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def _init_crm_funnel_conversion_group4(self):
        group_funnel_conversion4 = self.env.ref('of_sale_custom_workflow.group_funnel_conversion4')
        if not self.env['ir.values'].search(
                [('name', '=', 'of_display_funnel_conversion4'), ('model', '=', 'sale.config.settings')]):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_display_funnel_conversion4', True)
            self.env.ref('sales_team.group_sale_salesman').write({'implied_ids': [(4, group_funnel_conversion4.id)]})

    of_recalcul_date_confirmation = fields.Selection(string=u"(OF) Recalcul de la date d'enregistrement")
    group_funnel_conversion4 = fields.Boolean(
        string=u"Affichage du tunnel de conversion brut",
        implied_group='of_sale_custom_workflow.group_funnel_conversion4',
        group='sales_team.group_sale_salesman')
    of_display_funnel_conversion4 = fields.Boolean(
        string=u"(OF) Affichage du tunnel de conversion brut", default=True)

    @api.multi
    def set_of_display_funnel_conversion4(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_display_funnel_conversion4', self.of_display_funnel_conversion4)

    @api.onchange('of_display_funnel_conversion4')
    def _onchange_of_display_funnel_conversion4(self):
        if self.of_display_funnel_conversion4:
            self.update({'group_funnel_conversion4': True})
        else:
            self.update({'group_funnel_conversion4': False})
