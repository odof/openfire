# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_contract_count = fields.Integer(
        compute="_compute_of_contract_count", string="Nombre de contrats", oldname='of_contrat_count')
    of_contract_ids = fields.One2many(
        comodel_name='of.contract', inverse_name='partner_id', string="Contrats", oldname='of_contrat_ids')
    of_contract_line_count = fields.Integer(
        compute="_compute_of_contract_count", string="Nombre de lignes de contrat (prestataire)",
        oldname='of_contrat_line_count')
    of_contract_line_ids = fields.One2many(
        comodel_name='of.contract.line', inverse_name='supplier_id', string="Lignes de contrat (prestataire)",
        oldname='of_contract_line_count_ids')
    of_contract_line_address_count = fields.Integer(
            compute="_compute_of_contract_count", string="Nombre de lignes de contrat (addresse)")
    of_contract_line_address_ids = fields.One2many(
            comodel_name='of.contract.line', inverse_name='address_id', string="Lignes de contrat (addresse)")
    of_client_payeur_id = fields.Many2one('res.partner', string="Client payeur")
    of_client_receveur_ids = fields.One2many('res.partner', 'of_client_payeur_id', string="Clients receveurs")
    of_client_receveur_count = fields.Integer(
        compute="_compute_of_client_receveur_count", string="Nombre de clients receveurs")
    of_prestataire_id = fields.Many2one(
        comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]", track_visibility='onchange')
    of_code_magasin = fields.Char(string="Code magasin")

    @api.depends('of_contract_ids', 'of_contract_line_ids', 'of_contract_line_address_ids')
    def _compute_of_contract_count(self):
        for partner in self:
            partner.of_contract_count = len(partner.of_contract_ids)
            partner.of_contract_line_count = len(partner.of_contract_line_ids)
            partner.of_contract_line_address_count = len(partner.of_contract_line_address_ids)

    @api.depends('of_client_receveur_ids')
    def _compute_of_client_receveur_count(self):
        for partner in self:
            partner.of_client_receveur_count = len(partner.of_client_receveur_ids)

    @api.onchange('of_secteur_tech_id')
    def _onchange_of_secteur_tech_id(self):
        self.ensure_one()
        if self.of_secteur_tech_id:
            if self.of_secteur_tech_id.partner_id:
                self.of_prestataire_id = self.of_secteur_tech_id.partner_id.id
            if self.of_secteur_tech_id.type == 'tech_com':
                self.of_secteur_com_id = self.of_secteur_tech_id.id

    @api.multi
    def action_view_contract(self):
        action = self.env.ref('of_contract_custom.of_contract_custom_open_contrat').read()[0]
        action['domain'] = [('partner_id', 'in', self._ids)]
        return action

    @api.multi
    def action_view_contract_line(self):
        action = self.env.ref('of_contract_custom.of_contract_custom_open_contrat_line').read()[0]
        action['domain'] = [('supplier_id', 'in', self._ids)]
        return action

    @api.multi
    def action_view_contrat_line_address(self):
        action = self.env.ref('of_contract_custom.of_contract_custom_open_contrat_line').read()[0]
        action['domain'] = [('address_id', 'in', self._ids)]
        return action

    @api.multi
    def action_view_clients_receveurs(self):
        partners = self.mapped('of_client_receveur_ids')
        action = self.env.ref('contacts.action_contacts').read()[0]
        if len(partners) == 1:
            action['views'] = [(self.env.ref('base.view_partner_form').id, 'form')]
            action['res_id'] = partners.id
        else:
            action['domain'] = [('of_client_payeur_id', 'in', self._ids)]
        return action
