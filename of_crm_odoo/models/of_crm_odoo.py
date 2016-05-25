# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class crm_lead(osv.Model):
    _inherit = 'crm.lead'

    _columns = {
        'website': fields.char('Website', help="Website of Lead"),
        'tag_ids': fields.many2many('res.partner.category', 'crm_lead_res_partner_category_rel', 'lead_id', 'category_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service"),
    }

    # Recuperation du site web a la selection du partenaire
    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = super(crm_lead,self).on_change_partner_id(cr, uid, ids, partner_id, context=context)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            res['value']['website'] = partner.website
        return res

    # Transfert du site web a la creation du partenaire
    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        partner_obj = self.pool.get('res.partner')
        partner_id = super(crm_lead,self)._lead_create_contact(cr, uid, lead, name, is_company, parent_id=parent_id, context=context)
        if lead.website:
            partner_obj.write(cr, uid, partner_id, {'website': lead.website}, context=context)
        return partner_id

    # Recherche du code postal en mode prefixe
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'zip' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
                args[pos] = ('zip', '=like', args[pos][2]+'%')
            pos += 1
        return super(crm_lead, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)

class crm_team(osv.Model):
    _inherit = 'crm.team'

    # retrait des filtres de recherche par defaut dans la vue 'Votre pipeline'
    def action_your_pipeline(self, cr, uid, context=None):
        action = super(crm_team,self).action_your_pipeline(cr, uid, context=context)
        action['context'] = {key:val for key,val in action['context'].iteritems() if not key.startswith('search_default_')}
        return action

class res_partner(osv.osv):
    _inherit = 'res.partner'

    # Modification du crm.lead.tag en res.partner.category
    def make_opportunity(self, cr, uid, ids, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None, context=None):
        tag_obj = self.pool['crm.lead.tag']
        self.pool['crm.lead.tag'] = self.pool['res.partner.category']
        try:
            res = super(res_partner,self).make_opportunity(cr, uid, ids, opportunity_summary, planned_revenue=planned_revenue,
                                                           probability=probability, partner_id=partner_id, context=context)
        finally:
            self.pool['crm.lead.tag'] = tag_obj
        return res
