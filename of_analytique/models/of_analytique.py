# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_project_id'] = self.project_id and self.project_id.id or False
        return invoice_vals


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_compte_analytique = fields.Boolean(
        string="(OF) Analytique", readonly=True, states={'draft': [('readonly', False)]})

    @api.multi
    def set_of_compte_analytique_setting(self):
        view = self.env.ref('of_analytique.of_analytique_sale_order')
        if view:
            self.env.ref('of_analytique.of_analytique_sale_order').write({'active': self.of_compte_analytique})
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_compte_analytique',
            self.of_compte_analytique)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_project_id = fields.Many2one('account.analytic.account', string='Compte analytique')

    @api.onchange('of_project_id')
    def _onchange_project_id(self):
        self.ensure_one()
        if self.of_project_id:
            for line in self.invoice_line_ids:
                line.account_analytic_id = self.of_project_id.id
