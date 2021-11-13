# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_project_id'] = self.project_id and self.project_id.id or False
        return invoice_vals

    def action_confirm(self):
        config_preset_account = self.env['ir.values'].get_default('sale.config.settings', 'of_analytique_preset')
        config_analytic_code = self.env['ir.values'].get_default('sale.config.settings', 'of_analytique_code')
        # Génération/association automatique de compte analytique à la validation du bon de commande.
        for order in self:
            if order.project_id:
                continue
            partner = order.partner_id
            if config_preset_account and partner.contract_ids:
                # Utilisation d'un compte analytique existant poru le client
                order.project_id = partner.contract_ids[0]
            elif config_analytic_code:
                # Création d'un compte analytique pour le client
                company = order.company_id or self.env.user.company_id
                accounting_company = getattr(company, 'accounting_company_id', company)
                eval_vals = {
                    'order': order,
                    'company': company,
                    'accounting_company': accounting_company,
                    'partner': order.partner_id,
                }
                name, code = safe_eval(config_analytic_code, eval_vals)
                analytic = self.env['account.analytic.account'].create({
                    'name': name,
                    'code': code,
                    'company_id': accounting_company.id,
                    'partner_id': partner.id
                })
                order.project_id = analytic
        super(SaleOrder, self).action_confirm()


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_compte_analytique = fields.Boolean(
        string="(OF) Analytique")
    of_analytique_preset = fields.Boolean(
        string="(OF) Analytique",
        help=u"Remplir automatiquement le compte analytique du devis à sa confirmation avec le premier compte "
             u"analytique déjà existant pour le client.")
    of_analytique_code = fields.Char(
        string="(OF) Code analytique",
        help=u"Si ce champ est rempli, le code sera utilisé pour générer automatiquement un compte "
             u"analytique pour le client à la confirmation d'un devis.\n"
             u"Laisser vide pour ne pas générer de compte analytique automatiquement.")

    @api.multi
    def set_of_compte_analytique_setting(self):
        view = self.env.ref('of_analytique.of_analytique_sale_order')
        if view:
            self.env.ref('of_analytique.of_analytique_sale_order').write({'active': self.of_compte_analytique})
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_compte_analytique',
            self.of_compte_analytique)

    @api.multi
    def set_of_analytique_preset_setting(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_analytique_preset',
            self.of_analytique_preset)

    @api.multi
    def set_of_analytique_code_setting(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_analytique_code',
            self.of_analytique_code)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_project_id = fields.Many2one(
        'account.analytic.account', string='Compte analytique', readonly=True, states={'draft': [('readonly', False)]})

    @api.onchange('of_project_id')
    def _onchange_project_id(self):
        self.ensure_one()
        if self.of_project_id:
            for line in self.invoice_line_ids:
                line.account_analytic_id = self.of_project_id.id
