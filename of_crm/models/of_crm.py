# -*- coding: utf-8 -*-

#from openerp.osv import fields, osv
from openerp import models, fields, api

class crm_lead(models.Model):
    _inherit = 'crm.lead'

    of_website = fields.Char('Site web', help="Website of Lead", oldname="website")
    tag_ids = fields.Many2many('res.partner.category', 'crm_lead_res_partner_category_rel', 'lead_id', 'category_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service", oldname="of_tag_ids")
    
    # Récupération du site web à la sélection du partenaire
    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = super(crm_lead,self).on_change_partner_id(cr, uid, ids, partner_id, context=context)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            res['value']['of_website'] = partner.website
        return res

    # Transfert du site web à la création du partenaire
    @api.model
    def _lead_create_contact(self, lead, name, is_company, parent_id=False):
        partner_id = super(crm_lead,self)._lead_create_contact(lead, name, is_company, parent_id=parent_id)
        if lead.of_website:
            self.env['res.partner'].browse(partner_id).write({'website': lead.of_website})
        return partner_id

    # Recherche du code postal en mode préfixe
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'zip' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
                args[pos] = ('zip', '=like', args[pos][2]+'%')
            pos += 1
        return super(crm_lead, self).search(args, offset=offset, limit=limit, order=order, count=count)

class crm_team(models.Model):
    _inherit = 'crm.team'

    # Retrait des filtres de recherche par défaut dans la vue 'Votre pipeline'
    @api.model
    def action_your_pipeline(self):
        action = super(crm_team,self).action_your_pipeline()
        action['context'] = {key:val for key,val in action['context'].iteritems() if not key.startswith('search_default_')}
        return action

class res_partner(models.Model):
    _inherit = 'res.partner'

    # Modification du crm.lead.tag en res.partner.category
    @api.multi
    def make_opportunity(self, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None):
        tag_obj = self.env['crm.lead.tag']
        self.env['crm.lead.tag'] = self.env['res.partner.category']
        try:
            res = super(res_partner,self).make_opportunity(opportunity_summary, planned_revenue=planned_revenue, probability=probability, partner_id=partner_id)
        finally:
            self.env['crm.lead.tag'] = tag_obj
        return res
    

###############
# Projets CRM #
###############


# class of_crm_fam(osv.Model):
#     _name = "of.crm.fam"
#     _description = "Famille de projet"
#     _columns = {
#         'name': fields.char('Famille de projet', size=64, required=True),
#     }
# 
# class of_crm_type(osv.Model):
#     _name = "of.crm.type"
#     _description = "Type de Projet"
#     _columns = {
#         'name': fields.char('Type de projet', size=64, required=True),
#         'famille': fields.many2one('of.crm.fam', 'Famille de projet', required=True),
#     }
# 
# class of_crm_style(osv.Model):
#     _name = "of.crm.style"
#     _description = "Style de Projet"
#     _columns = {
#         'name': fields.char('Style', size=64, required=True),
#         'projet': fields.many2one('of.crm.type', 'Type de projet', required=True),
#     }
# 
# class of_crm_projet(osv.Model):
#     _name = "of.crm.projet"
#     _description = "Projet"
# 
#     def _get_name(self, cr, uid, id=0, table=None):
#         if table != None and id != 0:
#             cr.execute("SELECT name from " + str(table) + " WHERE id=" + str(id))
#             pre = cr.fetchone()[0]
#             return pre
#         else:
#             return ""
# 
#     def _get_famille(self, cr, uid, ids, name, arg, context=None):
#         res = {}
#         for p in self.browse(cr, uid, ids):
#             res[p.id] = p.fam_id.name
#         return res
# 
#     def _get_proba_ca(self, cr, uid, ids, name, arg, context=None):
#         tre = {}
#         for i in self.browse(cr, uid, ids):
#             tre[i.id] = round(((i.planned_revenue * i.probability) / 100), 2)
#         return tre
# 
#     _columns = {
#         #general
#         'name': fields.char(u'Libell\u00E9', size=128),
#         'date': fields.datetime('Date'),
#         'date_min':fields.function(lambda *a, **k:{}, method=True, type='date', string=u"Date creation min"),
#         'date_max':fields.function(lambda *a, **k:{}, method=True, type='date', string=u"Date creation max"),
#         'case_id': fields.many2one('of.crm', 'Prospect', ondelete='cascade'),
#         'state': fields.selection([('Planifie', 'Planifie'), ('Realise', 'Realise'), ('Annule', 'Annule')], 'Etat', size=16),
#         'note': fields.text('Description'),
#         'magasin': fields.related('case_id', 'magasin', type='many2one', relation="sale.shop", string="Magasin", store=True),
#         'user_id': fields.many2one('res.users', 'Auteur'),
#         #Permis de construire
#         'pc' : fields.boolean('Permis de construire'),
#         'adresse1': fields.char('Adresse1', size=128),
#         'adresse2': fields.char('Adresse2', size=128),
#         'ville': fields.char('Ville', size=128),
#         'cp': fields.char('Code postal', size=5),
#         'num_per': fields.char('No de permis', size=128),
#         #budget/financement
#         'planned_proba': fields.function(_get_proba_ca, store=True, method=True, string='CA', type='float', readonly=True),
#         'planned_revenue': fields.float('Montant'),
#         'planned_cost': fields.float('Cout'),
#         'probability': fields.float('Probabilite (%)'),
#         'paiement' : fields.selection([('cp', 'Comptant'), ('cr', 'A credit')], 'Financement'),
#         'mensua': fields.float('Mensualite', size=16),
#         #type de projet
#         'fam_id': fields.many2one('of.crm.fam', 'Famille'),
#         'famille': fields.function(_get_famille, store=True, method=True, string='Famille', type='char', size=16),
#         'type_id': fields.many2one('of.crm.type', 'Type', domain="[('famille','=',fam_id)]"),
#         'style_id': fields.many2one('of.crm.style', 'Style', domain="[('projet','=',type_id)]"),
#         #Batiment
#         'sp_dm_maison': fields.boolean('Maison'),
#         'sp_dm_appart': fields.boolean('Appartement'),
#         'sp_dm_rsecond': fields.boolean('R Secondaire'),
#         'sp_dm_locat': fields.boolean('Locataire'),
#         'sp_dm_proprio': fields.boolean('Proprietaire'),
#         'pr_dm_const': fields.boolean('En construction'),
#         'pr_dm_renov': fields.boolean('En renovation'),
#         'pr_dm_rachat': fields.boolean('En rachat'),
#         'exist' : fields.selection([('m2', 'Moins de 2 ans'), ('p2', 'Plus de 2 ans')], 'Existant depuis'),
#         'construct': fields.char('Nom du constructeur', size=64),
#         'd_reception': fields.datetime('Date de reception'),
#         'surface': fields.char('Surface en m2', size=16),
#         'lieu': fields.char('Adresse du site', size=64),
#         #conduit et pose
#         'type_pose' : fields.selection([('ns', 'Par nos soins'), ('cl', 'Par le client')], 'Pose'),
#         'pose_delai':  fields.selection(DELAIS, 'Delai', size=64),
#         'pose_eche': fields.datetime('Echeance'),
#         #energie
#         #'energie': fields.selection([('Bois', 'Bois'), ('Ethanol', 'Ethanol'), ('Gaz', 'Gaz'), ('Pellet', 'Pellet')]),
#         'energie': fields.selection([('Bois', 'Bois'), ('Ethanol', 'Ethanol'), ('Gaz', 'Gaz'), (u'Granul\u00E9', u'Granul\u00E9')]),
#     }
# 
#     _order = 'date desc'
# 
#     _defaults = {
#         'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:00'),
#         'pc': lambda *a: False,
#         'state': lambda *a: 'Planifie',
#         'probability': lambda *a: 100.00,
#     }
# 
#     def name_get(self, cr, uid, ids, context={}):
#         if not len(ids):
#             return []
#         rec_name = 'name'
# 
#         res = [(r['id'], r[rec_name]) for r in self.read(cr, uid, ids, [rec_name], context)]
#         return res
# 
#     def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=80):
#         if not args:
#             args = []
#         if not context:
#             context = {}
#         ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
#         if not ids:
#             ids = self.search(cr, uid, args, limit=limit, context=context)
#         return self.name_get(cr, uid, ids, context)
# 
#     def plafond_proba(self, cr, uid, ids, part=0, price=0):
#         return False
#         result = {}
#         if part < 0: part = 0
#         if part > 100:
#             proba = part / 10
#             if proba > 100:
#                 proba = proba / 10
#                 if proba > 100: proba = 100
#         else: proba = part
#         result['probability'] = round(proba, 2)
#         if price != 0: result['planned_proba'] = round(((proba * price) / 100), 2)
#         else: result['planned_proba'] = 0
#         return {'value':result}
# 
#     def onchange_famille(self, cr, uid, ids, fam=False, magp=False, userp=False, case=False):
#         res = {}
#         if fam: res['famille'] = self._get_name(cr, uid, fam, 'of_crm_fam')
#         else : res['famille'] = False
#         if case:
#             obj_case = self.pool.get("of.crm")
#             ids = obj_case.search(cr, uid, [('id', '=', case)])
#             for c in obj_case.read(cr, uid, ids):
#                 res['magasin'] = c["magasin"]
#                 res['user_id'] = c["user_id"]
#         if userp: res['user_id'] = userp
#         if magp: res['magasin'] = magp
#         res['style_id'] = False
#         res['type_id'] = False
#         return {'value':res}
