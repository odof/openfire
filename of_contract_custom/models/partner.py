# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_contrat_count = fields.Integer(compute="_compute_of_contrat_count", string="Nombre de contrat")
    of_contrat_ids = fields.One2many(comodel_name='of.contract', inverse_name='partner_id', string="Contrats")
    of_contrat_line_count = fields.Integer(compute="_compute_of_contrat_count", string="Nombre de ligne de contrat")
    of_contract_line_count_ids = fields.One2many(
        comodel_name='of.contract.line', inverse_name='supplier_id', string="Lignes de contrat")
    of_prestataire_id = fields.Many2one(
        comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]", track_visibility='onchange')
    of_code_magasin = fields.Char(string="Code magasin")

    @api.depends('of_contrat_ids', 'of_contract_line_count_ids')
    def _compute_of_contrat_count(self):
        for partner in self:
            partner.of_contrat_count = len(partner.of_contrat_ids)
            partner.of_contrat_line_count = len(partner.of_contract_line_count_ids)

    @api.onchange('of_secteur_tech_id')
    def _onchange_of_secteur_tech_id(self):
        self.ensure_one()
        if self.of_secteur_tech_id:
            if self.of_secteur_tech_id.partner_id:
                self.of_prestataire_id = self.of_secteur_tech_id.partner_id.id
            if self.of_secteur_tech_id.type == 'tech_com':
                self.of_secteur_com_id = self.of_secteur_tech_id.id

    @api.multi
    def action_view_contrat(self):
        action = self.env.ref('of_contract_custom.of_contract_custom_open_contrat').read()[0]
        action['domain'] = [('partner_id', 'in', self._ids)]
        return action

    @api.multi
    def action_view_contrat_line(self):
        action = self.env.ref('of_contract_custom.of_contract_custom_open_contrat_line').read()[0]
        action['domain'] = [('supplier_id', 'in', self._ids)]
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_of_contract_service_form_planning').read()[0]
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_contract_custom.view_of_contract_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.id,
            'default_address_id': self.address_get(adr_pref=['delivery']) or self.id,
            'default_recurrence': False,
            'default_date_next' : fields.Date.today(),
            'default_origin'    : u"[Partenaire] " + self.name,
            'hide_bouton_planif': True,
            'default_type_id': self.env.ref('of_contract_custom.of_contract_custom_type_maintenance').id,
            }
        return action
