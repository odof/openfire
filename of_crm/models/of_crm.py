# -*- coding: utf-8 -*-

import time
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import models, fields, api

class Lead(models.Model):
    _inherit = 'crm.lead'

    of_website = fields.Char('Site web', help="Website of Lead")
    tag_ids = fields.Many2many('res.partner.category', 'crm_lead_res_partner_category_rel', 'lead_id', 'category_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service", oldname="of_tag_ids")
    of_description_projet = fields.Html('Notes de projet')
    of_ref = fields.Char(string="Référence",copy=False)
    of_prospecteur = fields.Many2one("res.users",string="Prospecteur")
    of_date_prospection = fields.Date(string="Date de prospection")
    of_date_cloture = fields.Date(string="Date de clôture")
    of_infos_compl = fields.Text(string="Autres infos")
    geo_lat = fields.Float(string='Geo Lat', digits=(8, 8))
    geo_lng = fields.Float(string='Geo Lng', digits=(8, 8))

    # Récupération du site web à la sélection du partenaire
    def _onchange_partner_id_values(self, partner_id):
        res = super(Lead, self)._onchange_partner_id_values(partner_id)

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)

            res['of_website'] = partner.website
            res['geo_lat'] = partner.geo_lat
            res['geo_lng'] = partner.geo_lng
        return res

    """@api.model
    def _onchange_stage_id_values(self, stage_id):
        values = super(Lead,self)._onchange_stage_id_values(stage_id)
        proba = getattr(values,'probability',1)
        if proba == 0.0:
            pass

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        super(Lead,self)._onchange_stage_id()
        proba = getattr(self,'probability',1)
        if proba in (0.0,100.0):
            self.of_date_cloture = time.strftime(DEFAULT_SERVER_DATE_FORMAT)"""

    # Transfert du site web à la création du partenaire
    @api.multi
    def _lead_create_contact(self, name, is_company, parent_id=False):
        """ extract data from lead to create a partner
            :param name : furtur name of the partner
            :param is_company : True if the partner is a company
            :param parent_id : id of the parent partner (False if no parent)
            :returns res.partner record
        """
        partner = super(Lead, self)._lead_create_contact(name, is_company, parent_id=parent_id)
        if self.of_website:
            partner.website = self.of_website
        if self.geo_lat:
            partner.geo_lat = self.geo_lat
        if self.geo_lng:
            partner.geo_lng = self.geo_lng
        return partner

    # Recherche du code postal en mode préfixe
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'zip' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
                args[pos] = ('zip', '=like', args[pos][2]+'%')
            pos += 1
        return super(Lead, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def action_set_lost(self):
        """ surcharge sans appel à super(), une opportunité perdue n'est pas forcément archivée 
            fonction appelée depuis le wizard de motif de perte
        """
        for lead in self:
            stage_id = lead._stage_find(domain=[('probability', '=', 0.0), ('on_change', '=', True)])
            lead.write({'stage_id': stage_id.id,
                        'probability': 0,
                        'of_date_cloture': time.strftime(DEFAULT_SERVER_DATE_FORMAT),
                        })
        return True

    @api.multi
    def action_set_won(self):
        res = super(Lead,self).action_set_won()
        for lead in self:
            lead.of_date_cloture = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return res

    """@api.multi
    def write(self,vals):
        res = super(Lead,self).write(vals)
        if len(self) == 1:
            proba = self.probability
            if proba in (0.0,100.0):
                self.write({'of_date_cloture': time.strftime(DEFAULT_SERVER_DATE_FORMAT)})
        elif len(self) >= 1:
            proba = self._ids[0].probability
            if proba in (0.0,100.0):
                self.write({'of_date_cloture': time.strftime(DEFAULT_SERVER_DATE_FORMAT)})
        return res"""

class Team(models.Model):
    _inherit = 'crm.team'

    # Retrait des filtres de recherche par défaut dans la vue 'Votre pipeline'
    @api.model
    def action_your_pipeline(self):
        action = super(Team, self).action_your_pipeline()
        action['context'] = {key: val for key, val in action['context'].iteritems() if not key.startswith('search_default_')}
        return action

class OFUtmMedium(models.Model):
    _inherit = 'utm.medium'

    source_id = fields.Many2one('utm.source',string='Origine par défaut')

class OFUtmMixin(models.AbstractModel):
    _inherit = 'utm.mixin'

    @api.multi
    @api.onchange('medium_id')
    def _onchange_medium_id(self):
        self.ensure_one()
        if self.medium_id and self.medium_id.source_id:
            self.source_id = self.medium_id.source_id
