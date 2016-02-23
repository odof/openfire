# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp import models, api
import pyodbc
import time
import logging
_logger = logging.getLogger(__name__)


class of_parc_installe(osv.Model):

    _inherit = 'of.parc.installe'
     
    _columns={
         'chiffre_aff_ht': fields.float('Chiffre d\'affaire HT', help=u"Chiffre d\'affaire HT"),
         'quantite_vendue': fields.float(u'Quantité vendue', help=u"Quantité vendue"),
         'marge': fields.float(u'Marge', help=u"Marge"),
    }
#     
#     # Désactiver contrainte car plusieurs no série identique possible
#     #_sql_constraints = [('no_serie_uniq', 'unique(name)', 'Ce numéro de série est déjà utilisé et doit être unique.')]



class project_issue(osv.Model):
    _name = "project.issue"
    _inherit = "project.issue"

    _columns = {
        'of_type': fields.selection([('contacttel',u'ASS'), ('di',u'DI')], 'Type', required=False, help=u"Type de SAV"),
        'of_actions_eff': fields.text(u'Actions à effectuer'),
        'of_actions_realisees': fields.text(u'Actions réalisées'),
        'description': fields.text(u'Problématique'), # Existe déjà, pour renommer champ
        'of_contact_sav': fields.char(u'Contact SAV', size=64),
        'of_contact_address': fields.related('partner_id', 'contact_address', readonly=True, type='char', string=u'Adresse partenaire'),
        'of_tel_sav': fields.char(u'Tél. SAV', size=64),
        'of_tags_parent': fields.related('partner_id', 'category_ids', readonly=True, type='many2many', string=u'Etiquettes parent'),
    }
    
    _defaults = {
        'of_type': 'contacttel',
    }


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
    _inherit = "res.partner"

    _columns = {
        'of_payeur_id': fields.many2one('res.partner', 'Client payeur', required=False,  domain="[('parent_id','=',False)]", ondelete='restrict'),
        'of_ape': fields.char("Code APE", size=16, required=False),
        'contact_ids': fields.one2many('res.partner', 'parent_id', 'Contacts', domain=[('active','=',True),('type','!=','delivery')]),
        'livraison_ids': fields.one2many('res.partner', 'parent_id', 'Lieu livraison', domain=[('active','=',True),('type','=','delivery')]),
        'of_id_sage_contact': fields.integer("ID Sage des contacts"),
        'of_id_sage_livraison': fields.integer("ID Sage des lieux de livraison")
    }

#     _sql_constraints = [
#         #('ref_uniq', 'unique(ref)', 'Le n° de compte client est déjà utilisé et doit être unique.'),
#         #('of_id_sage_contact_uniq', 'unique(of_id_sage_contact)', 'of_id_sage_contact doit être unique.'),
#         #('of_id_sage_livraison_uniq', 'unique(of_id_sage_livraison)', 'of_id_sage_livraison doit être unique.')
#     ]

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
class of_sage_winterhalter(models.AbstractModel):
    
    _name="of.sage.winterhalter"
    
    @api.model
    def synchro_sage(self, dsn, utilisateur, mdp, base):
        
        date_debut_sync = time.strftime('%Y-%m-%d')
        
        # On récupère la date de la dernière mise à jour si elle existe
        ir_values_obj = self.env['ir.values']
        ir_values = ir_values_obj.search([('name','=', 'dern_sync_sage_winterhalter'),('model', '=', 'of.sage.winterhalter')])
        
        if not ir_values:
            date_dern_modif = '2015-11-01'
        else:
            date_dern_modif = ir_values[0].value

        _logger.info('#OFW# Synchronisation depuis Sage depuis le %s', date_dern_modif)
        
        # On se connecte à la base Sage de Winterhalter par ODBC
        con_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, utilisateur, mdp, base)
        
        try:
            conn = pyodbc.connect(con_string)
        except:
            _logger.error('#OFW# Erreur de connexion à la base Sage')
            return False
            
        curs = conn.cursor()
        
        res_country_obj = self.env['res.country']
        
        #
        # CLIENTS (sans les contacts/lieu de livraison)
        #
         
        _logger.info('#OFW# Synchronisation des clients depuis Sage')
        curs.execute("SELECT * FROM "+base+".dbo.F_COMPTET WHERE cbModification>='"+date_dern_modif+"' ORDER BY cbModification ASC;")
        partenaires = curs.fetchall()
        #_logger.info("#OFW# Partenaires : %s", partenaires)
        res_partner_obj = self.env['res.partner']
        for i in partenaires:
            _logger.info("#OFW# Dans Sage : %s %s %s", i.CT_Num, i.CT_Intitule, i.cbModification)
            if i.CT_Num.strip():
                # Il y a un no de compte
                res_partner_ids = res_partner_obj.search([('ref','=', i.CT_Num),'|',('active', '=', True),('active', '=', False)])
                value = {'ref': (i.CT_Num or '').strip()}
                # Si 1ère lettre no compte est F alors est un fournisseur, C client
                if value['ref'][0].upper() == 'F':
                    value['customer'] = False
                    value['supplier'] = True
                else:
                    value['customer'] = True
                    value['supplier'] = False 
                if i.CT_Intitule.strip():
                    value['name'] = (i.CT_Intitule or '').strip()
                else:
                    _logger.info("#OFW# Erreur partenaire : le client %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", i.CT_Num)
                    continue
                if i.CT_Sommeil:
                    value['active'] = False
                else:
                    value['active'] = True
                value['street'] = (i.CT_Adresse or '').strip()
                value['street2'] = (i.CT_Complement or '').strip()
                value['zip'] = (i.CT_CodePostal or '').strip()
                value['city'] = (i.CT_Ville or '').strip()
                value['country_id'] = (i.CT_Pays or '').strip()
                # On affecte l'id du pays de la liste dans la base Oddo si on le reconnait, sinon on le met en texte après la ville
                if value['country_id']:
                    res_country_ids = res_country_obj.search([('name','=ilike', value['country_id'])])
                    if res_country_ids:
                        value['country_id'] = res_country_ids[0].id
                    else:
                        value['city'] = value['city'] + " - " + value['country_id']
                        value['country_id'] = ''
                value['website'] = (i.CT_Site or '').strip()
                value['phone'] = (i.CT_Telephone or '').strip()
                value['fax'] = (i.CT_Telecopie or '').strip()
                value['email'] = (i.CT_EMail or '').strip()
                value['of_ape'] = (i.CT_Ape or '').strip()
                
                if i.CT_NumPayeur.strip():
                    # Client payeur, on vérifie qu'il existe dans Odoo
                    res_partner_payeur_ids = res_partner_obj.search([('ref','=', i.CT_NumPayeur.strip()),'|',('active', '=', True),('active', '=', False)])
                    
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
        curs.execute("SELECT * FROM "+base+".dbo.F_LIVRAISON WHERE cbModification>='"+date_dern_modif+"' ORDER BY cbModification ASC;")
        partenaires = curs.fetchall()
        #_logger.info("#OFW# Livraison : %s", partenaires)
        for i in partenaires:
            value = {}
            _logger.info("#OFW# Dans Sage : %s %s %s", i.CT_Num, i.LI_Intitule, i.cbModification)
            if i.CT_Num.strip(): # Il y a un no de compte parent
                if i.LI_No: # Si différent de 0
                    res_partner_ids = res_partner_obj.search([('of_id_sage_livraison','=', i.LI_No),'|',('active', '=', True),('active', '=', False)])
                else:
                    res_partner_ids = ''
                
                value['of_id_sage_livraison'] = i.LI_No or 0
                value['customer'] = True
                value['supplier'] = False

                if (i.LI_Intitule or '').strip():
                    value['name'] = i.LI_Intitule.strip()
                else:
                    _logger.info("#OFW# Erreur livraison : le lieu de livraison LI_No %s de la société %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", i.LI_No, i.CT_Num)                    
                    continue

                # Parent, on vérifie qu'il existe dans Odoo
                res_partner_parent_ids = res_partner_obj.search([('ref','=', i.CT_Num.strip()),'|',('active', '=', True),('active', '=', False)])
                if res_partner_parent_ids:
                    value['parent_id'] = res_partner_parent_ids[0].id
                else:
                    # Le compte client parent n'existe pas. On n'enregistre pas et génère une erreur.
                    _logger.info("#OFW# Erreur livraison : le lieu de livraison %s (id sage contact %s) pointe vers un client parent (%s) qui n'existe pas dans Odoo. Non créé/modifié dans Odoo.", value['name'], i.LI_No, i.CT_Num)
                    continue

                value['type'] = 'delivery'
                value['street'] = (i.LI_Adresse or '').strip()
                value['street2'] = (i.LI_Complement or '').strip()
                value['zip'] = (i.LI_CodePostal or '').strip()
                value['city'] = (i.LI_Ville or '').strip()
                value['country_id'] = (i.LI_Pays or '').strip()
                # On affecte l'id du pays de la liste dans la base Oddo si on le reconnait, sinon on le met en texte après la ville
                if value['country_id']:
                    res_country_ids = res_country_obj.search([('name','=ilike', value['country_id'])])
                    if res_country_ids:
                        value['country_id'] = res_country_ids[0].id
                    else:
                        value['city'] = value['city'] + " - " + value['country_id']
                        value['country_id'] = ''
                value['phone'] = (i.LI_Telephone or '').strip()
                value['fax'] = (i.LI_Telecopie or '').strip()
                value['email'] = (i.LI_EMail or '').strip()
                
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
        curs.execute("SELECT * FROM "+base+".dbo.F_CONTACTT WHERE cbModification>='"+date_dern_modif+"' ORDER BY cbModification ASC;")
        partenaires = curs.fetchall()
        #_logger.info("#OFW# Contacts : %s", partenaires)
        for i in partenaires:
            value = {}
            _logger.info("#OFW# Dans Sage : %s %s %s", i.CT_Nom, i.CT_Prenom, i.cbModification)
            if i.CT_Num and i.CT_Num.strip(): # Il y a un no de compte parent (pour parent_id dans Odoo)
                if i.CT_No: # Si différent de 0
                    res_partner_ids = res_partner_obj.search([('of_id_sage_contact','=', i.CT_No),'|',('active', '=', True),('active', '=', False)])
                else:
                    res_partner_ids =''
                
                value['of_id_sage_contact'] = i.CT_No
                
                if i.CT_Nom and i.CT_Nom.strip():
                    value['name'] = i.CT_Nom.strip()
                if i.CT_Prenom and i.CT_Prenom.strip():
                    value['name'] = value['name'] + ' ' + i.CT_Prenom.strip()
                if not value['name']:
                    _logger.info("#OFW# Erreur contact : le contact CT_No %s de la société %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", i.CT_No, i.CT_Num)
                    continue
                                                                                                                                                
                # Parent, on vérifie qu'il existe dans Odoo
                res_partner_parent_ids = res_partner_obj.search([('ref','=', i.CT_Num.strip()),'|',('active', '=', True),('active', '=', False)])
                if res_partner_parent_ids:
                    value['parent_id'] = res_partner_parent_ids[0].id
                else:
                    # Le compte client parent n'existe pas. On n'enregistre pas et génère une erreur.
                    _logger.info("#OFW# Erreur contact : le contact %s (id sage contact %s) pointe vers un client parent (%s) qui n'existe pas dans Odoo. Non créé/modifié dans Odoo.", value['name'], i.CT_No, i.CT_Num)
                    continue
                
                value['customer'] = True
                value['supplier'] = False
                value['type'] = 'contact'
                value['phone'] = (i.CT_Telephone or '').strip()
                value['fax'] = (i.CT_Telecopie or '').strip()
                value['mobile'] = (i.CT_TelPortable or '').strip()
                value['email'] = (i.CT_EMail or '').strip()
                value['function'] = (i.CT_Fonction or '').strip()

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
        

        #
        # ARTICLES
        #
        
        _logger.info('#OFW# Synchronisation des articles depuis Sage')
        curs.execute("SELECT * FROM "+base+".dbo.F_ARTICLE WHERE cbModification>='"+date_dern_modif+"' ORDER BY cbModification ASC;")
        articles = curs.fetchall()
        #_logger.info("#OFW# Articles : %s", articles)
        res_product_obj = self.env['product.template']
        for i in articles:
            _logger.info("#OFW# Dans Sage : [%s] %s %s", i.AR_Ref, i.AR_Design, i.cbModification)
            if i.AR_Ref.strip():
                # Il y a une référence d'article
                res_product_ids = res_product_obj.search([('default_code','=', i.AR_Ref),'|',('active', '=', True),('active', '=', False)])
                value = {'default_code': i.AR_Ref}
                if (i.AR_Design or '').strip():
                    value['name'] = i.AR_Design.strip()
                else:
                    _logger.info("#OFW# Erreur article : l'article %s n'a pas de nom dans Sage (champ obligatoire dans Odoo). Non créé/modifié dans Odoo.", value['default_code'])
                    continue
                if i.AR_Sommeil:
                    value['active'] = False
                else:
                    value['active'] = True
                value['type'] = 'product'
                value['list_price'] = (i.AR_PrixVen or '')
                value['standard_price'] = (i.AR_PrixAch or '')
                value['sale_ok'] = True
                value['purchase_ok'] = True
                if (i.Produit_dangereux or '').upper() == 'OUI': 
                    value['of_est_dangereux'] = True
                else:
                    value['of_est_dangereux'] = False
                value['weight'] = (i.AR_PoidsBrut or '')
                value['of_poids_adr'] = (i.Poids_ADR_ or '')
                # Article de substitution, on vérifie qu'il existe dans Odoo
                value['of_produit_substitue_id'] = (i.AR_Substitut or '').strip()

                if value['of_produit_substitue_id']:
                    res_product_substitue_ids = res_product_obj.search([('default_code','=', value['of_produit_substitue_id']),'|',('active', '=', True),('active', '=', False)])
                    if res_product_substitue_ids:
                        value['of_produit_substitue_id'] = res_product_substitue_ids[0].id
                    else:
                        # L'article n'existe pas. On n'enregistre pas et génère une erreur.
                        _logger.info("#OFW# Erreur article : l'article de substitution %s de l'article [%s] %s n'existe pas dans Odoo. Non créé/modifié dans Odoo.", value['of_produit_substitue_id'], value['default_code'], value ['name'])
                        continue
               
                # Catégorie de produit, on vérifie qu'elle existe dans Odoo
                if (i.FA_CodeFamille or '').strip():
                    res_categ_ids = self.env['product.category'].search([('name','=', (i.FA_CodeFamille or '').strip())])
                    if res_categ_ids:
                        value['categ_id'] = res_categ_ids[0].id
                    else:
                        # La catégorie n'existe pas. On l'enregistre mais avec la catégorie par défaut d'Odoo.
                        _logger.info("#OFW# Erreur article : la catégorie %s de l'article [%s] %s n'existe pas dans Odoo. Enregistré mais avec la catégorie d'article par défaut d'Odoo.", (i.FA_CodeFamille or '').strip(), value['default_code'], value['name'])
                
                # Unité de mesure
                value['uom_id'] = i.AR_UniteVen
                if value['uom_id'] == 2:
                    value['uom_id'] = self.env.ref('product.product_uom_cm').id
                elif value['uom_id'] == 3:
                    value['uom_id'] = self.env.ref('product.product_uom_meter').id
                elif value['uom_id'] == 4:
                    value['uom_id'] = self.env.ref('product.product_uom_gram').id
                elif value['uom_id'] == 5:
                    value['uom_id'] = self.env.ref('product.product_uom_kgm').id
                elif value['uom_id'] == 13:
                    value['uom_id'] = self.env.ref('product.product_uom_hour').id
                else:
                    value['uom_id'] = self.env.ref('product.product_uom_unit').id

                value['uom_po_id'] = value['uom_id']

                #_logger.info('#OFW# value = %s', value)
                
                # Si l'article n'existe pas dans Odoo, on le créer, sinon on le met à jour
                if not res_product_ids:
                    res_product_obj.create(value)
                    _logger.info("#OFW# Article [%s] %s créé", value['default_code'], value['name'])
                    
                elif len(res_product_ids) == 1:
                    # Il n'y a bien qu'un article dans Odoo avec cette référence. On le met à jour.
                    res_product_ids.write(value)
                    _logger.info("#OFW# Article [%s] %s modifié", value['default_code'],value['name'])
                
                else:
                    # Il existe plusieurs articles dans Odoo avec cette référence. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                    _logger.info("#OFW# Erreur : l'article [%s] %s dans Sage existe en plusieurs exemplaires dans Odoo avec cette référence. Non créé/modifié dans Odoo.", value['default_code'], value['name'])
            
            else:
                # Il n'y a pas de référence d'article, on ne peut pas enregistrer
                _logger.info("#OFW# Erreur article : l'article %s, prix vente %s, prix achat %s, code famille %s, n'a pas de référence dans Sage. Non créé/modifié dans Odoo.", i.AR_Design, i.AR_PrixVen, i.AR_PrixAchat, i.FA_CodeFamille)
        
        # On enregistre la date de mise à jour dans la configuration
        if not ir_values:
            ir_values.create({'name': 'dern_sync_sage_winterhalter', 'value': date_debut_sync, 'model': 'of.sage.winterhalter'})
        else:
            ir_values[0].write({'name': 'dern_sync_sage_winterhalter', 'value': date_debut_sync, 'model': 'of.sage.winterhalter'})
        
        # On ferme la connexion sqlserver
        curs.close()
        del curs
        conn.close()
        
        return True

