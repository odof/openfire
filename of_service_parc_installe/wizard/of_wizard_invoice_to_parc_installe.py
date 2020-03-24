# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfInvoiceLineToParcInstalleWizard(models.TransientModel):
    _name = "of.invoice.line.to.parc.installe.wizard"

    @api.model
    def _get_domain_product(self):
        active_id = self._context.get('active_id')
        if not active_id:
            return []
        invoice_lines = self.env['account.invoice'].browse(active_id).invoice_line_ids
        return [('default_code', 'in', invoice_lines.mapped('product_id').mapped('default_code'))]

    @api.model
    def _get_client_id_default(self):
        active_id = self._context.get('active_id')
        if not active_id:
            return
        return self.env['account.invoice'].browse(active_id).partner_id

    @api.model
    def _get_revendeur_installateur_id_default(self):
        active_id = self._context.get('active_id')
        if not active_id:
            return
        return self.env['account.invoice'].browse(active_id).company_id.partner_id

    @api.model
    def _get_date_service_default(self):
        active_id = self._context.get('active_id')
        if not active_id:
            return
        return self.env['account.invoice'].browse(active_id).date_invoice

    name = fields.Char(string=u"N° de série")
    product_id = fields.Many2one('product.product', string=u"Produit installé", domain=_get_domain_product)
    client_id = fields.Many2one('res.partner', string="Client", default=_get_client_id_default)
    site_adresse_id = fields.Many2one('res.partner', string='Site installation')
    revendeur_id = fields.Many2one('res.partner', string="Revendeur", default=_get_revendeur_installateur_id_default)
    installateur_id = fields.Many2one('res.partner', string="Installateur", default=_get_revendeur_installateur_id_default)
    date_service = fields.Date(string="Date vente", default=_get_date_service_default)
    invoice_id = fields.Many2one('account.invoice', default=lambda w: w._context.get('active_id'))

    @api.multi
    def create_parc_installe(self):
        parc_obj = self.env['of.parc.installe']
        data = {
            'name': self.name if self.name else False,
            'product_id': self.product_id.id if self.product_id else False,
            'client_id': self.client_id.id if self.client_id else False,
            'site_adresse_id': self.site_adresse_id.id if self.site_adresse_id else False,
            'revendeur_id': self.revendeur_id.id if self.revendeur_id else False,
            'installateur_id': self.installateur_id.id if self.installateur_id else False,
            'date_service': self.date_service if self.date_service else False,
            'account_invoice_ids' : [(4, self.invoice_id.id)] if self.invoice_id else [],
        }
        parc = parc_obj.create(data)
        parc.onchange_product_id()
        return parc

    @api.multi
    def create_and_display_parc_installe(self):
        return {
            'name': u'Parc installé',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('of_parc_installe.of_parc_installe_form_view').id,
            'res_model': 'of.parc.installe',
            'type': 'ir.actions.act_window',
            'res_id': self.create_parc_installe().id,
            'context': self._context,
        }
