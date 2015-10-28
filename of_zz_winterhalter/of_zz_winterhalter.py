# -*- coding: utf-8 -*-
##############################################################################
#
#   OpenERP, Open Source Management Solution
#   Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#   $Id$
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
        'chiffre_aff_ht': fields.float('Chiffre d\'affaire HT', help=u"Chiffre d\'affaire HT"),
        'quantite_vendue': fields.float(u'Quantité vendue', help=u"Quantité vendue"),
        'marge': fields.float(u'Marge', help=u"Marge"),
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


class project_issue(osv.Model):
    _name = "project.issue"
    _inherit = "project.issue"

    _columns = {
        'of_produit_installe_id': fields.many2one('of.parc.installe', 'Produit installé', readonly=False),
        'of_type': fields.selection([('contacttel',u'Appel assistance téléphonique'), ('di',u'Demande d\'intervention')], 'Type', required=False, help=u"Type de SAV"),
        'product_name_id': fields.many2one('product.product', 'Désignation', ondelete='restrict'),
        #'product_name_id': fields.related('of_produit_installe_id', 'product_id', 'name', readonly=True, type='char', string=u'Nom'),
        'product_category_id': fields.related('product_name_id', 'categ_id', 'name', readonly=True, type='char', string=u'Famille'),
        'of_actions_eff': fields.text(u'Actions à effectuer'),
        'of_actions_realisees': fields.text(u'Actions réalisées'),
        'description': fields.text(u'Problématique'), # Existe déjà, pour renommer champ
    }
    
    _defaults = {
        'of_type': 'contacttel',
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

    
    def ouvrir_demande_intervention(self, cr, uid, context={}):
        # Ouvre une demande d'intervenion depuis un SAV (normalement contact téléphonique) en reprenant les renseignements du SAV en cours.
        # Objectif : permettre de déclencher rapidement une demande d'intervention après un contact téléphonique sans à avoir à resaisir les champs
        
        if not context:
            context = {}
        res = {
            'name': 'Demande intervention',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.issue',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        
        # On récupère les données du SAV courant
        if 'active_ids' in context.keys():
            active_ids = isinstance(context['active_ids'], (int,long)) and [context['active_ids']] or context['active_ids']
            if active_ids:
                project_issue = self.browse(cr, uid, active_ids[0])
                if project_issue.partner_id:
                    res['context'] = {'default_partner_id': project_issue.partner_id.id,
                        'default_name': project_issue.name,
                        'default_of_type': 'di',
                        'default_of_produit_installe_id': project_issue.of_produit_installe_id.id,
                        'default_email_from': project_issue.email_from,
                        'default_priority': project_issue.priority,
                        # M9 'default_categ_id': project_issue.categ_id.id,
                        # M9 'default_date_deadline': project_issue.date_deadline,
                        'default_of_garantie': project_issue.of_garantie,
                        'default_of_payant_client': project_issue.of_payant_client,
                        'default_of_payant_fournisseur': project_issue.of_payant_fournisseur,
                        }
                else:
                    return False
        return res


class res_partner(osv.Model):
    _name = "res.partner"
    _inherit = "res.partner"
    
    _columns = {
        'of_revendeur': fields.boolean('Revendeur', help="Cocher cette case si ce partenaire est un revendeur."),
        'of_installateur': fields.boolean('Installateur', help="Cocher cette case si ce partenaire est un installateur."),
        'of_payeur_id': fields.many2one('res.partner', 'Client payeur', required=False,  domain="[('parent_id','=',False)]", ondelete='restrict'),
        'of_ape': fields.char("Code APE", size=16, required=False),
        'contact_ids': fields.one2many('res.partner', 'parent_id', 'Contacts', domain=[('active','=',True),('type','!=','delivery')]),
        'livraison_ids': fields.one2many('res.partner', 'parent_id', 'Lieu livraison', domain=[('active','=',True),('type','=','delivery')]),
    }
    
    _sql_constraints = [('ref_uniq', 'unique(ref)', 'Le n° de compte client est déjà utilisé et doit être unique.')]


class product_template(osv.Model):
    _name = "product.template"
    _inherit = "product.template"
    
    _columns = {
        'of_est_dangereux': fields.boolean(u'Produit dangereux', help=u"Cocher cette case si ce produit est dangereux."),
        'of_poids_adr': fields.float(u'Poids ADR', help=u"Poids ADR"),
        'of_pas_dans_sage': fields.boolean(u'Pas dans Sage', help=u"Si ce produit n'est pas dans Sage."),
        'of_produit_substitue_id': fields.many2one('product.template', 'Article de substitution', required=False,  ondelete='restrict'),
    }
    
 
