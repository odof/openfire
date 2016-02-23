# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
import time


class of_parc_installe(osv.Model):
    """
    Parc installée
    """
    _name = 'of.parc.installe'
    _description = "Parc installé"
    
    _columns={
        'name': fields.char("No de série", size=64, required=False),
        'date_service': fields.date('Date vente', required=False),
        'date_installation': fields.date('Date d\'installation', required=False),
        'product_id': fields.many2one('product.product', 'Produit', required=True, ondelete='restrict'),
        'product_category_id': fields.related('product_id', 'categ_id', 'name', readonly=True, type='char', string=u'Famille'),
        'client_id': fields.many2one('res.partner', 'Client', required=True, domain="[('parent_id','=',False)]", ondelete='restrict'),
        'site_adresse_id': fields.many2one('res.partner', 'Site installation', required=False, domain="['|',('parent_id','=',client_id),('id','=',client_id)]", ondelete='restrict'),
        'revendeur_id': fields.many2one('res.partner', 'Revendeur', required=False,  domain="[('of_revendeur','=',True)]", ondelete='restrict'),
        'installateur_id': fields.many2one('res.partner', 'Installateur', required=False, domain="[('of_installateur','=',True)]", ondelete='restrict'),
        'installateur_adresse_id': fields.many2one('res.partner', 'Adresse installateur', required=False, domain="['|',('parent_id','=',installateur_id),('id','=',installateur_id)]", ondelete='restrict'),
        'note': fields.text('Note'),
        'tel_site_id': fields.related('site_adresse_id', 'phone', readonly=True, type='char', string=u'Téléphone site installation'),
        'street_site_id': fields.related('site_adresse_id', 'street', readonly=True, type='char', string=u'Adresse'),
        'street2_site_id': fields.related('site_adresse_id', 'street2', readonly=True, type='char', string=u'Complément adresse'),
        'zip_site_id': fields.related('site_adresse_id', 'zip', readonly=True, type='char', string=u'Code postal'),
        'city_site_id': fields.related('site_adresse_id', 'city', readonly=True, type='char', string=u'Ville'),
        'country_site_id': fields.related('site_adresse_id', 'country_id', readonly=True, type='many2one', relation="res.country", string=u'Pays'),
        'no_piece': fields.char(u'N° pièce', size=64, required=False),
        #'chiffre_aff_ht': fields.float('Chiffre d\'affaire HT', help=u"Chiffre d\'affaire HT"),
        #'quantite_vendue': fields.float(u'Quantité vendue', help=u"Quantité vendue"),
        #'marge': fields.float(u'Marge', help=u"Marge"),
        'project_issue_ids': fields.one2many('project.issue', 'of_produit_installe_id', 'SAV'),
    }
    
    # Désactiver contrainte car plusieurs no série identique possible
    #_sql_constraints = [('no_serie_uniq', 'unique(name)', 'Ce numéro de série est déjà utilisé et doit être unique.')]
    
    
    def action_creer_sav(self, cr, uid, context={}):
        if not context:
            context = {}
        res = {
            'name': 'SAV',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        if 'active_ids' in context.keys():
            active_ids = isinstance(context['active_ids'], (int,long)) and [context['active_ids']] or context['active_ids']
            if active_ids:
                parc_installe = self.browse(cr, uid, active_ids[0])
                if parc_installe.client_id:
                    res['context'] = {'default_partner_id': parc_installe.client_id.id,
                                      'default_of_produit_installe_id': parc_installe.id,
                                      'default_of_type': 'di'}
        return res

class res_partner(osv.Model):
    _inherit = "res.partner"

    _columns = {
        'of_revendeur': fields.boolean('Revendeur', help="Cocher cette case si ce partenaire est un revendeur."),
        'of_installateur': fields.boolean('Installateur', help="Cocher cette case si ce partenaire est un installateur."),
    }


class project_issue(osv.Model):
    _name = "project.issue"
    _inherit = "project.issue"

    _columns = {
        'of_produit_installe_id': fields.many2one('of.parc.installe', 'Produit installé', readonly=False),
        'product_name_id': fields.many2one('product.product', 'Désignation', ondelete='restrict'),
        'product_category_id': fields.related('product_name_id', 'categ_id', 'name', readonly=True, type='char', string=u'Famille'),
    }
    
    
    def on_change_of_produit_installe_id(self, cr, uid, ids, of_produit_installe_id, context=None):
        # Si le no de série est saisi, on met le produit du no de série du parc installé. 
        if of_produit_installe_id:
            parc = self.pool.get('of.parc.installe').browse(cr, uid, of_produit_installe_id, context=context)
            if parc and parc.product_id:
                return {'value': {'product_name_id': parc.product_id.id}}
        return
    
    def on_change_product_name_id(self, cr, uid, ids, of_produit_installe_id, context=None):
        # Si un no de série est saisie, on force le produit lié au no de série.
        # Si pas de no de série, on laisse la possibilité de choisir un article
        res = False
        if of_produit_installe_id: # Si no de série existe, on récupère l'article associé
            res = self.on_change_of_produit_installe_id(cr, uid, ids, of_produit_installe_id, context)
        return res
    

