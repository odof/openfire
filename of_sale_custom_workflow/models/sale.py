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
        sale_responsible = self.env.user.has_group('sales_team.group_sale_manager')
        action = False
        for order in self:
            article_principal = order.order_line.filtered('of_article_principal')
            if not self._context.get('no_verif_margin', False) and article_principal \
                    and article_principal[0].product_id.categ_id.of_taux_marge:
                if int(order.of_marge_pc) < article_principal[0].product_id.categ_id.of_taux_marge:
                    message = u"Le montant de marge de la commande %s est de %.2f%% alors que la catégorie %s de " \
                              u"l'article principal %s %s une marge minimum de %s%%" % (
                                  order.name,
                                  order.of_marge_pc,
                                  article_principal[0].product_id.categ_id.name,
                                  article_principal[0].product_id.display_name,
                                  sale_responsible and u"demande" or u"requiert",
                                  article_principal[0].product_id.categ_id.of_taux_marge)
                    action = self.env['of.popup.wizard'].popup_return(message=message, titre=u"Contrôle de marge")
                if not sale_responsible and action:
                    return action
            order.state = 'presale'
            order.of_custom_confirmation_date = fields.Datetime.now()
            if not self._context.get('order_cancellation', False):
                order.with_context(auto_followup=True, followup_creator_id=self.env.user.id).sudo().\
                    action_followup_project()
        if sale_responsible and action:
            return action
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
