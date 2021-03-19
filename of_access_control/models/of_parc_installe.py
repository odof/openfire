# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    # Default #

    @api.model
    def _default_company(self):
        # Pour les objets du planning, le choix de société se fait par un paramètre de config
        if self.env['ir.values'].get_default('of.intervention.settings', 'company_choice') == 'user':
            return self.env['res.company']._company_default_get('of.parc.installe')
        return False

    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", default=lambda s: s._default_company())

    @api.onchange('client_id')
    def _onchange_client_id(self):
        super(OFParcInstalle, self)._onchange_client_id()
        if self.client_id and not self.site_adresse_id:
            # Pour les objets du planning, le choix de la société se fait par un paramètre de config
            company_choice = self.env['ir.values'].get_default(
                'of.intervention.settings', 'company_choice') or 'contact'
            if company_choice == 'contact' and self.client_id.company_id:
                self.company_id = self.client_id.company_id.id

    @api.onchange('site_adresse_id')
    def _onchange_site_adresse_id(self):
        if self.site_adresse_id:
            # Pour les objets du planning, le choix de la société se fait par un paramètre de config
            company_choice = self.env['ir.values'].get_default(
                'of.intervention.settings', 'company_choice') or 'contact'
            if company_choice == 'contact' and self.site_adresse_id.company_id:
                self.company_id = self.site_adresse_id.company_id.id
