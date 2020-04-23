# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

    @api.multi
    def action_confirm(self):
        """
        Un prospect devient signé sur confirmation de commande
        """
        res = super(SaleOrder, self).action_confirm()
        partners = self.env['res.partner']
        for order in self:
            if order.partner_id.of_customer_state == 'lead' and order.partner_id not in partners:
                partners += order.partner_id
        partners.write({'of_customer_state': 'customer'})
        return res


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        partners = self.env['res.partner']
        for invoice in self:
            if invoice.partner_id.of_customer_state == 'lead' and invoice.partner_id not in partners and \
                    invoice.partner_id.customer:
                partners += invoice.partner_id
        partners.write({'of_customer_state': 'customer'})
        return res
