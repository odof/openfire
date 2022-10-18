# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model_cr_context
    def _auto_init(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_sale_custom_workflow'), ('state', 'in', ['installed', 'to upgrade'])])
        res = super(SaleOrder, self)._auto_init()
        if module_self:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_self.latest_version
            if version < '10.0.2':
                cr = self.env.cr
                cr.execute("""
                -- update of_custom_confirmation_delta
                UPDATE sale_order SO
                SET of_custom_confirmation_delta = EXTRACT(EPOCH FROM (SO.of_custom_confirmation_date::timestamp - SO.date_order::timestamp)) / 86400.0
                WHERE SO.of_custom_confirmation_date IS NOT NULL AND SO.date_order IS NOT NULL AND SO.state IN ('presale', 'sale', 'done', 'closed');

                -- update of_confirmation_delta
                UPDATE sale_order SO
                SET of_confirmation_delta = EXTRACT(EPOCH FROM (SO.confirmation_date::timestamp - SO.of_custom_confirmation_date::timestamp)) / 86400.0
                WHERE SO.of_custom_confirmation_date IS NOT NULL AND SO.date_order IS NOT NULL AND SO.state IN ('sale', 'done', 'closed');""")
        return res


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
    of_custom_confirmation_delta = fields.Float(
        string=u"Délai de confirmation", digits=(4, 1), readonly=True, copy=False)
    of_confirmation_delta = fields.Float(string=u"Délai d'enregistrement", digits=(4, 1), readonly=True, copy=False)

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
            of_custom_confirmation_date = fields.Datetime.now()
            order.of_custom_confirmation_date = of_custom_confirmation_date
            if order.date_order:
                date_order = datetime.strptime(order.date_order, "%Y-%m-%d %H:%M:%S")
                of_custom_confirmation_date = datetime.strptime(of_custom_confirmation_date, "%Y-%m-%d %H:%M:%S")
                of_custom_confirmation_delta = of_custom_confirmation_date - date_order
                # We use a float to avoid rounding the result
                order.of_custom_confirmation_delta = of_custom_confirmation_delta.total_seconds() / 86400.0
        self.activate_activities_triggered_at_validation()
        return True

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            of_custom_confirmation_date = datetime.strptime(order.of_custom_confirmation_date, "%Y-%m-%d %H:%M:%S")
            if order.confirmation_date:
                confirmation_date = datetime.strptime(order.confirmation_date, "%Y-%m-%d %H:%M:%S")
                of_confirmation_delta = confirmation_date - of_custom_confirmation_date
                # We use a float to avoid rounding the result
                order.of_confirmation_delta = of_confirmation_delta.total_seconds() / 86400.0
        return res

    @api.multi
    def action_reopen(self):
        self.ensure_one()
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
