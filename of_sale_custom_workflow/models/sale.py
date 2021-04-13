# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


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

    @api.multi
    def action_preconfirm(self):
        for order in self:
            order.state = 'presale'
            order.of_custom_confirmation_date = fields.Datetime.now()
            if not self._context.get('order_cancellation', False):
                order.with_context(auto_followup=True, followup_creator_id=self.env.user.id).sudo().\
                    action_followup_project()
        return True

    @api.multi
    def action_reopen(self):
        self.ensure_one()
        # On ré-ouvre le suivi
        if self.of_followup_project_id:
            self.of_followup_project_id.set_to_in_progress()
        self.state = 'sale'
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    confirmation_date_order = fields.Datetime(string=u"Date d'enregistrement de commande")
    of_confirmation_date = fields.Datetime(string=u"Date d'enregistrement")


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
