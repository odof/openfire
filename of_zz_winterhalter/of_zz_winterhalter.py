# -*- coding: utf-8 -*-

from openerp import models, api
from openerp.osv import fields, osv
import pyodbc

import logging
_logger = logging.getLogger(__name__)
#import time


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
        'of_type': fields.selection([('contacttel',u'ASS'), ('di',u'DI')], 'Type', required=False, help=u"Type de SAV"),
        'product_name_id': fields.many2one('product.product', 'Désignation', ondelete='restrict'),
        #'product_name_id': fields.related('of_produit_installe_id', 'product_id', 'name', readonly=True, type='char', string=u'Nom'),
        'product_category_id': fields.related('product_name_id', 'categ_id', 'name', readonly=True, type='char', string=u'Famille'),
        'of_actions_eff': fields.text(u'Actions à effectuer'),
        'of_actions_realisees': fields.text(u'Actions réalisées'),
        'description': fields.text(u'Problématique'), # Existe déjà, pour renommer champ
        'of_contact_sav': fields.char(u'Contact SAV', size=64),
        'of_tel_sav': fields.char(u'Tél. SAV', size=64)
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
            'res_model': 'project.issue',
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
                        'default_of_categorie_id': project_issue.of_categorie_id.id,
                        'default_date_deadline': project_issue.date_deadline,
                        'default_tag_ids': [(6,0,[tag.id for tag in project_issue.tag_ids])],
                        'default_description': project_issue.description,
                        'default_of_actions_realisees': project_issue.of_actions_realisees,
                        'default_of_actions_eff': project_issue.of_actions_eff
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
        'of_id_sage_contact': fields.integer("ID Sage des contacts"),
        'of_id_sage_livraison': fields.integer("ID Sage des lieux de livraison")
    }
    
    _sql_constraints = [
        ('ref_uniq', 'unique(ref)', 'Le n° de compte client est déjà utilisé et doit être unique.'),
        ('of_id_sage_contact_uniq', 'unique(of_id_sage_contact)', 'of_id_sage_contact doit être unique.'),
        ('of_id_sage_livraison_uniq', 'unique(of_id_sage_livraison)', 'of_id_sage_livraison doit être unique.')    
    ]


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
                partner = self.browse(cr, uid, active_ids[0])
                res['context'] = {
                    'default_partner_id': partner.id,
                    'default_of_type': 'di'
                }
        return res


class product_template(osv.Model):
    _name = "product.template"
    _inherit = "product.template"
    
    _columns = {
        'of_est_dangereux': fields.boolean(u'Produit dangereux', help=u"Cocher cette case si ce produit est dangereux."),
        'of_poids_adr': fields.float(u'Poids ADR', help=u"Poids ADR"),
        'of_pas_dans_sage': fields.boolean(u'Pas dans Sage', help=u"Si ce produit n'est pas dans Sage."),
        'of_produit_substitue_id': fields.many2one('product.template', 'Article de substitution', required=False,  ondelete='restrict'),
    }

# Pour la synchronisation des données depuis Sage
class sage(models.AbstractModel):
    _name="sage"
    
    @api.model
    def synchro_sage(self, dsn, utilisateur, mdp, base):
        
        date_modif = '2015-12-03'

        con_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, utilisateur, mdp, base)
        conn = pyodbc.connect(con_string)
        curs = conn.cursor()
        
        res_country_obj = self.env['res.country']
        
        #
        # CLIENTS (sans les contacts/lieu de livraison)
        #
         
        _logger.info('#OFW# Synchronisation des clients depuis Sage')
        curs.execute("SELECT * FROM "+base+".dbo.F_COMPTET WHERE cbModification>='"+date_modif+"' ORDER BY cbModification ASC;")
        partenaires = curs.fetchall()
        #_logger.info("#OFW# Partenaires : %s", partenaires)
        res_partner_obj = self.env['res.partner']
        for i in partenaires:
            #_logger.info("Dans Sage : %s %s %s", i.CT_Num, i.CT_Intitule, i.cbModification)
            if i.CT_Num.strip():
                # Il y a un no de compte
                res_partner_ids = res_partner_obj.search([('ref','=', i.CT_Num),'|',('active', '=', True),('active', '=', False)])
                value = {'ref': i.CT_Num.strip()}
                # Si 1ère lettre no compte est F alors est un fournisseur, C client
                if value['ref'][0].upper() == 'F':
                    value['customer'] = False
                    value['supplier'] = True
                else:
                    value['customer'] = True
                    value['supplier'] = False 
                if i.CT_Intitule.strip():
                    value['name'] = i.CT_Intitule.strip()
                else:
                    _logger.info("#OFW# Erreur partenaire : le client %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", i.CT_Num)
                    continue
                if i.CT_Sommeil:
                    value['active'] = False
                else:
                    value['active'] = True
                value['street'] = i.CT_Adresse.strip()
                value['street2'] = i.CT_Complement.strip()
                value['zip'] = i.CT_CodePostal.strip()
                value['city'] = i.CT_Ville.strip()
                value['country_id'] = i.CT_Pays.strip()
                # On affecte l'id du pays de la liste dans la base Oddo si on le reconnait, sinon on le met en texte après la ville
                if value['country_id']:
                    res_country_ids = res_country_obj.search([('name','=ilike', value['country_id'])])
                    if res_country_ids:
                        value['country_id'] = res_country_ids[0].id
                    else:
                        value['city'] = value['city'] + " - " + value['country_id']
                        value['country_id'] = ''
                value['website'] = i.CT_Site.strip()
                value['phone'] = i.CT_Telephone.strip()
                value['fax'] = i.CT_Telecopie.strip()
                value['email'] = i.CT_EMail.strip()
                value['of_ape'] = i.CT_Ape.strip()
                
                if i.CT_NumPayeur.strip():
                    # Client payeur, on vérifie qu'il existe dans Odoo
                    res_partner_payeur_ids = res_partner_obj.search([('ref','=', i.CT_NumPayeur.strip())])
                    
                    if res_partner_payeur_ids:
                        value['of_payeur_id'] = res_partner_payeur_ids[0].id
                    elif value['ref'] != i.CT_NumPayeur.strip():
                        # Le compte payeur n'existe pas et ce n'est pas le même que le compte. On n'enregistre pas et génère une erreur.
                        # Si c'était le même et que c'est une création, on doit l'enregistrer une fois que le compte principal a été créé
                        _logger.info("#OFW# Erreur partenaire : le client %s pointe vers un client payeur (%s) qui n'existe pas dans Odoo. Non créé/modifié dans Odoo.", i.CT_Num, i.CT_NumPayeur)
                        continue

                #_logger.info('#OFW# value = %s', value)
                #_logger.info('#OFW# res_partner_ids = %s', res_partner_ids)
                
                # Si le client n'existe pas dans Odoo, on le crée, sinon on le met à jour
                if not res_partner_ids:
                    res_partner_obj.create(value)
                    _logger.info("#OFW# Partenaire %s %s créé", i.CT_Num, i.CT_Intitule)
                    
                    if value['ref'] == i.CT_NumPayeur.strip():
                        # Si le compte payeur est le même que le compte que l'on vient de créer, on l'ajoute.
                        res_partner_payeur_ids = res_partner_obj.search([('ref','=', i.CT_NumPayeur)])
                        
                        if res_partner_payeur_ids:
                            res_partner_payeur_ids.of_payeur_id = res_partner_payeur_ids[0].id
                
                elif len(res_partner_ids) == 1:
                    # Il y a qu'un client dans Odoo avec ce no de compte. On le met à jour.
                    res_partner_ids.write(value)
                    _logger.info("#OFW# Partenaire %s %s modifié", i.CT_Num, i.CT_Intitule)
                
                else:
                    # Il existe plusieurs clients dans Odoo avec ce no de compte. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    _logger.info("#OFW# Erreur : le no de compte client %s (%s) dans Sage existe en plusieurs exemplaires dans Odoo. Non créé/modifié dans Odoo.", i.CT_Num, i.CT_Intitule)
            
            else:
                # Il n'y a pas de no de compte, on ne peut pas enregistrer
                _logger.info("#OFW# Erreur partenaire : le client %s %s %s %s %s %s n'a pas de no de compte dans Sage. Non créé/modifié dans Odoo.", i.CT_Intitule, i.CT_Adresse, i.CT_Complement, i.CT_CodePostal, i.CT_Ville, i.CT_Site)


        #
        # LIEUX DE LIVRAISON
        #
         
        _logger.info('#OFW# Synchronisation des lieux de livraison depuis Sage')
        curs.execute("SELECT * FROM "+base+".dbo.F_LIVRAISON WHERE cbModification>='"+date_modif+"' ORDER BY cbModification ASC;")
        partenaires = curs.fetchall()
        #_logger.info("#OFW# Livraison : %s", partenaires)
        for i in partenaires:
            value = {}
            #_logger.info("Dans Sage : %s %s %s", i.CT_Num, i.LI_Intitule, i.cbModification)
            if i.CT_Num.strip(): # Il y a un no de compte parent
                if i.LI_No: # Si différent de 0
                    res_partner_ids = res_partner_obj.search([('of_id_sage_livraison','=', i.LI_No),'|',('active', '=', True),('active', '=', False)])
                else:
                    res_partner_ids =''
                
                value['of_id_sage_livraison'] = i.LI_No
                value['customer'] = True
                value['supplier'] = False

                if i.LI_Intitule.strip():
                    value['name'] = i.LI_Intitule.strip()
                else:
                    _logger.info("#OFW# Erreur livraison : le lieu de livraison LI_No %s de la société %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", i.LI_No, i.CT_Num)                    
                    continue

                # Parent, on vérifie qu'il existe dans Odoo
                res_partner_parent_ids = res_partner_obj.search([('ref','=', i.CT_Num.strip())])
                if res_partner_parent_ids:
                    value['parent_id'] = res_partner_parent_ids[0].id
                else:
                    # Le compte client parent n'existe pas. On n'enregistre pas et génère une erreur.
                    _logger.info("#OFW# Erreur livraison : le lieu de livraison %s (id sage contact %s) pointe vers un client parent (%s) qui n'existe pas dans Odoo. Non créé/modifié dans Odoo.", value['name'], i.LI_No, i.CT_Num)
                    continue

                value['type'] = 'delivery'
                value['street'] = i.LI_Adresse.strip()
                value['street2'] = i.LI_Complement.strip()
                value['zip'] = i.LI_CodePostal.strip()
                value['city'] = i.LI_Ville.strip()
                value['country_id'] = i.LI_Pays.strip()
                # On affecte l'id du pays de la liste dans la base Oddo si on le reconnait, sinon on le met en texte après la ville
                if value['country_id']:
                    res_country_ids = res_country_obj.search([('name','=ilike', value['country_id'])])
                    if res_country_ids:
                        value['country_id'] = res_country_ids[0].id
                    else:
                        value['city'] = value['city'] + " - " + value['country_id']
                        value['country_id'] = ''
                value['phone'] = i.LI_Telephone.strip()
                value['fax'] = i.LI_Telecopie.strip()
                value['email'] = i.LI_EMail.strip()
                
                #_logger.info('#OFW# value = %s', value)
                #_logger.info('#OFW# res_partner_ids = %s', res_partner_ids)
                
                # Si le lieu de livraison n'existe pas dans Odoo, on le crée, sinon on le met à jour
                if not res_partner_ids:
                    res_partner_obj.create(value)
                    _logger.info("#OFW# Lieu de livraison %s du client %s créé", value['name'], i.CT_Num)
                                    
                elif len(res_partner_ids) == 1:
                    # Il a qu'un lieu de livraison dans Odoo avec ce no d'indentifiant. On le met à jour.
                    res_partner_ids.write(value)
                    _logger.info("#OFW# Livraison %s (id livraison sage %s) du client %s modifié", value['name'], i.LI_No, i.CT_Num)
               
                else:
                     # Il existe plusieurs lieux de livraison dans Odoo avec ce no d'identifiant. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    _logger.info("#OFW# Erreur livraison : le lieu de livraison %s avec l'id sage livraison %s existe en plusieurs exemplaires dans Odoo. Non créé/modifié dans Odoo.", value['name'], i.LI_No)
            
            else:
                # Il n'y a pas de no de compte parent, on ne peut pas enregistrer
                _logger.info("#OFW# Erreur livraison : le lieu de livraison %s id sage livraison %s n'a pas de no de compte parent dans Sage. Non créé/modifié dans Odoo.", value['nane'], i.LI_No)


        #
        # CONTACTS (contacts)
        #

        _logger.info('#OFW# Synchronisation des contacts depuis Sage')
        curs.execute("SELECT * FROM "+base+".dbo.F_CONTACTT WHERE cbModification>='"+date_modif+"' ORDER BY cbModification ASC;")
        partenaires = curs.fetchall()
        #_logger.info("#OFW# Contacts : %s", partenaires)
        for i in partenaires:
            value = {}
            #_logger.info("Dans Sage : %s %s %s", i.CT_Nom, i.CT_Prenom, i.cbModification)
            if i.CT_Num.strip(): # Il y a un no de compte parent (pour parent_id dans Odoo)
                if i.CT_No: # Si différent de 0
                    res_partner_ids = res_partner_obj.search([('of_id_sage_contact','=', i.CT_No),'|',('active', '=', True),('active', '=', False)])
                else:
                    res_partner_ids =''
                
                value['of_id_sage_contact'] = i.CT_No
                
                if i.CT_Nom.strip():
                    value['name'] = i.CT_Nom.strip()
                if i.CT_Prenom.strip():
                    value['name'] = value['name'] + ' ' + i.CT_Prenom.strip()
                if not value['name']:
                    _logger.info("#OFW# Erreur contact : le contact CT_No %s de la société %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", i.CT_No, i.CT_Num)
                    continue
                                                                                                                                                
                # Parent, on vérifie qu'il existe dans Odoo
                res_partner_parent_ids = res_partner_obj.search([('ref','=', i.CT_Num.strip())])
                if res_partner_parent_ids:
                    value['parent_id'] = res_partner_parent_ids[0].id
                else:
                    # Le compte client parent n'existe pas. On n'enregistre pas et génère une erreur.
                    _logger.info("#OFW# Erreur contact : le contact %s (id sage contact %s) pointe vers un client parent (%s) qui n'existe pas dans Odoo. Non créé/modifié dans Odoo.", value['name'], i.CT_No, i.CT_Num)
                    continue

                value['customer'] = True
                value['supplier'] = False
                value['type'] = 'contact'
                value['phone'] = i.CT_Telephone.strip()
                value['fax'] = i.CT_Telecopie.strip()
                value['mobile'] = i.CT_TelPortable.strip()
                value['email'] = i.CT_EMail.strip()
                value['function'] = i.CT_Fonction.strip()

                #_logger.info('#OFW# value = %s', value)

                # Si le contact n'existe pas dans Odoo, on le crée, sinon on le met à jour
                if not res_partner_ids:
                    res_partner_obj.create(value)
                    _logger.info("#OFW# Contact %s du client %s créé", value['name'], i.CT_Num)

                elif len(res_partner_ids) == 1:
                    # Il a qu'un contact dans Odoo avec ce no d'indentifiant. On le met à jour.
                    res_partner_ids.write(value)
                    _logger.info("#OFW# Contact %s (id contact sage %s) du client %s modifié", value['name'], i.CT_No, i.CT_Num)

                else:
                    # Il existe plusieurs contacts dans Odoo avec ce no d'identifiant. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    _logger.info("#OFW# Erreur contact : le contact %s avec l'id sage contact %s existe en plusieurs exemplaires dans Odoo. Non créé/modifié dans Odoo.", value['name'], i.CT_No)

            else:
                # Il n'y a pas de no de compte parent, on ne peut pas enregistrer
                _logger.info("#OFW# Erreur contact : le contact %s %s id sage contact %s n'a pas de no de compte parent dans Sage. Non créé/modifié dans Odoo.", i.CT_Nom, i.CT_Prenom, i.CT_No)

        return True


        #
        # ARTICLES
        #
        
        _logger.info('#OFW# Synchronisation des articles depuis Sage')
        curs.execute("SELECT * FROM "+base+".dbo.F_ARTICLE WHERE cbModification>='"+date_modif+"' ORDER BY cbModification ASC;")
        articles = curs.fetchall()
        _logger.info("*OFW* Articles : %s", articles)
        res_product_obj = self.env['product.product']
        for i in articles:
            #_logger.info("Dans Sage : %s %s %s %s", i.CT_Num, i.CT_Intitule, i.cbModification, i.CT_Site)
            if i.AR_Ref.strip():
                # Il y a une référence d'article
                res_product_ids = res_product_obj.search([('default_code','=', i.Ar_Ref)])
                value = {'default_code': i.Ar_Ref}
                if i.Ar_Design.strip():
                    value['name'] = i.Ar_Design
                else:
                    _logger.info("#OFW# Erreur article : l'article %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", i.Ar_Design)
                    continue
                if i.AR_Sommeil:
                    value['active'] = False
                else:
                    value['active'] = True
                value['type'] = 'stockable product'
                value['list_price'] = i.AR_PrixVen
                value['standart_price'] = i.AR_PrixAch
                value['sale_ok'] = True
                value['purchase_ok'] = True
                value['of_est_dangereux'] = i.Produit_dangereux
                value['country_id'] = i.CT_Pays.strip()
                # On affecte l'id du pays de la liste dans la base Oddo si on le recoonait, sinon on le met en texte après la ville
                if value['country_id']:
                    res_country_ids = res_country_obj.search([('name','=ilike', value['country_id'])])
                    if res_country_ids:
                        value['country_id'] = res_country_ids[0].id
                    else:
                        value['city'] = value['city'] + " - " + value['country_id']
                        value['country_id'] = ''
                value['weight'] = i.AR_PoidsBrut
                value['of_poids_adr'] = i.Poids_ADR
                if i.CT_NumPayeur.strip():
                    # Client payeur, on vérifie qu'il existe dans Odoo
                    res_partner_payeur_ids = res_partner_obj.search([('ref','=', i.CT_NumPayeur.strip())])
                    
                    if res_partner_payeur_ids:
                        value['of_payeur_id'] = res_partner_payeur_ids[0].id
                    elif value['ref'] != i.CT_NumPayeur.strip():
                        # Le compte payeur n'existe pas et ce n'est pas le même que le compte. On n'enregistre pas et génère une erreur.
                        # Si c'était le même et que c'est une création, on doit l'enregistrer une fois que le compte principal a été créé
                        _logger.info("#OFW# Erreur partenaire : le client %s pointe vers un client payeur (%s) qui n'existe pas dans Odoo. Non créé/modifié dans Odoo.", i.CT_Num, i.CT_NumPayeur)
                        continue

                #_logger.info('*OFW* value = %s', value)
                
                # On teste si les champs obligatoires pour Odoo sont bien enregistrés. On n'enregistre rien sinon.
                # Si le clients n'existe pas dans Odoo, on le créer, sinon on le met à jour
                if not res_partner_ids:
                    res_partner_obj.create(value)
                    _logger.info("#OFW# Partenaire %s %s créé", i.CT_Num, i.CT_Intitule)
                    
                    if value['ref'] == i.CT_NumPayeur.strip():
                        # Si le compte payeur est le même que le compte que l'on vient de créer, on l'ajoute.
                        res_partner_payeur_ids = res_partner_obj.search([('ref','=', i.CT_NumPayeur)])
                        
                        if res_partner_payeur_ids:
                            res_partner_payeur_ids.of_payeur_id = res_partner_payeur_ids[0].id
                
                elif len(res_partner_ids) == 1:
                    # Il n'y a bien qu'un client dans Odoo avec ce no de compte. On le met à jour.
                    res_partner_ids.write(value)
                    _logger.info("#OFW# Partenaire %s %s %s modifié", i.CT_Num, i.CT_Intitule, i.CT_Sommeil)
                
                else:
                    # Il existe plusieurs clients dans Odoo avec ce no de compte. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    _logger.info("#*OFW# Erreur : le no de compte client %s (%s) dans Sage existe en plusieurs exemplaires dans Odoo. Non créé/modifié dans Odoo.", i.CT_Num, i.CT_Intitule)
            
            else:
                # Il n'y a pas de référence d'article, on ne peut pas enregistrer
                _logger.info("#*OFW# Erreur article : l'article %s, prix vente %s, prix achat %s, code famille %s, n'a pas de référence dans Sage. Non créé/modifié dans Odoo.", i.AR_Design, AR_PrixVen, AR_PrixAchat, FA_CodeFamille)
        
        return True
