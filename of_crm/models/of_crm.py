# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Lead(models.Model):
    _inherit = 'crm.lead'

    of_website = fields.Char('Site web', help="Website of Lead")
    tag_ids = fields.Many2many('res.partner.category', 'crm_lead_res_partner_category_rel', 'lead_id', 'category_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service", oldname="of_tag_ids")
    of_description_projet = fields.Html('Notes de projet')

    # Récupération du site web à la sélection du partenaire
    def _onchange_partner_id_values(self, partner_id):
        res = super(Lead, self)._onchange_partner_id_values(partner_id)

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)

            res['of_website'] = partner.website
        return res

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


class Team(models.Model):
    _inherit = 'crm.team'

    # Retrait des filtres de recherche par défaut dans la vue 'Votre pipeline'
    @api.model
    def action_your_pipeline(self):
        action = super(Team, self).action_your_pipeline()
        action['context'] = {key: val for key, val in action['context'].iteritems() if not key.startswith('search_default_')}
        return action
