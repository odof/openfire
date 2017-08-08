# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time, csv, base64
from StringIO import StringIO

class of_import(models.Model):
    _name = 'of.import'

    name = fields.Char('Nom', size=64, required=True)
    type_import = fields.Selection([('product.template', 'Articles'), ('res.partner', 'Partenaires'), ('crm.lead', u'Pistes/opportunités'), ('res.partner.bank', 'Comptes en banques partenaire'), ('of.service', 'Services Openfire')], string="Type d'import", required=True)
    date = fields.Datetime('Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), help=u"Date qui sera affectée aux imports comme date de valeur.")
    date_debut_import = fields.Datetime('Début', readonly=True)
    date_fin_import = fields.Datetime('Fin', readonly=True)
    prefixe = fields.Char(u'Préfixe référence', size=10, help=u"Texte qui précèdera la référence.")
    user_id = fields.Many2one('res.users', 'Utilisateur', readonly=True, default=lambda self: self._uid)
    file = fields.Binary('Fichier', required=True)
    file_name = fields.Char('Nom du fichier')
    separateur = fields.Char(u'Séparateur champs', help=u"Caractère séparateur des champs dans le fichier d'import.\nSi non renseigné, le système essaye de le déterminer lui même.\nMettre \\t pour tabulation.")
    state = fields.Selection([('brouillon', 'Brouillon'), ('importe', 'Importé'), ('annule', 'Annulé')], 'État', default='brouillon', readonly=True)
    nb_total = fields.Integer('Nombre total', readonly=True)
    nb_ajout = fields.Integer(u'Ajoutés', readonly=True)
    nb_maj = fields.Integer(u'Mis à jour', readonly=True)
    nb_echoue = fields.Integer(u'Échoués/ignorés', readonly=True)
    sortie_note = fields.Text('Note', compute='get_sortie_note', readonly=True)
    sortie_succes = fields.Text('Information', readonly=True)
    sortie_avertissement = fields.Text('Avertissements', readonly=True)
    sortie_erreur = fields.Text('Erreurs', readonly=True)
    
    def get_champs_odoo(self, model=''):
        "Renvoi un dictionnaire contenant les caractéristiques des champs Odoo en fonction du type d'import sélectionné (champ type_import)"

        if not model:
            return {}

        champs_odoo = {}

        #  On récupère la liste des champs de l'objet depuis ir.model.fields
        obj = self.env['ir.model.fields'].search([('model','=', model)])
        for champ in obj:
            champs_odoo[champ.name] = {
                'description': champ.field_description,
                'requis': champ.required,
                'type': champ.ttype,
                'relation': champ.relation,
                'relation_champ': champ.relation_field}

        # Des champs qui sont obligatoire peuvent avoir une valeur par défaut (donc in fine pas d'obligation de les renseigner).
        # On récupère les champs qui ont une valeur par défaut et on indique qu'ils ne sont pas obligatoire.
        champs_requis = [key for key,vals in champs_odoo.iteritems() if vals['requis']]
        for i in self.env[model].default_get(champs_requis):
            champs_odoo[i]['requis'] = False

        # On ne rend pas obligatoire manuellement un champ qui est marqué comme obligatiore car créé par la fonction create d'Odoo.
        if model == 'product.template' and 'product_variant_ids' in champs_odoo:
            champs_odoo['product_variant_ids']['requis'] = False

        return champs_odoo


    @api.depends('type_import')
    def get_sortie_note(self):
        "Met à jour la liste des champs Odoo disponibles pour l'import dans le champ note"
        for imp in self:
            sortie_note = ''
            for champ, valeur in self.get_champs_odoo(self.type_import).items():
                if champ in ('tz', 'lang'): # Champs qui plantent lors de l'import, on les ignore.
                    continue
                # sortie_note += "- " + valeur['description'] + " : " + champ + u" (type : " + valeur['type'] + u") relation : " + str(valeur['relation']) + u" relation champ  : " + str(valeur['relation_champ'])
                sortie_note += "- " + valeur['description'] + " : " + champ
                if valeur['type'] == 'selection':
                    sortie_note += u" [ valeurs autorisées : "
                    for cle in dict(self.env[self.type_import]._fields[champ].selection):
                        sortie_note += cle + " "
                    sortie_note += ']'
                sortie_note += '\n'
                    
            if sortie_note:
                sortie_note = u"Champs disponibles pour l'import (en-tête de colonne) :\n" + sortie_note
            imp.sortie_note = sortie_note

    @api.multi
    def bouton_remettre_brouillon(self):
        for imp in self:
            imp.state = 'brouillon'
        return True

    @api.multi
    def bouton_simuler(self):
        self.importer(simuler=True)
        return True
    
    @api.multi
    def bouton_importer(self):
        self.importer(simuler=False)
        return True
    
    @api.multi
    def importer(self, simuler=True):
        
#
# VARIABLES DE CONFIGURATION
#

        frequence_commit = 100 # Enregistrer (commit) tous les n enregistrements

        model = self.type_import # On récupère l'objet (model) à importer indiqué dans le champ type d'import
        model_obj = self.env[model]

        if model == 'product.template':
            nom_objet = 'article'              # Libellé pour affichage dans message information/erreur
            champ_primaire = 'default_code'    # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
            champ_reference = 'default_code'   # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
        elif model == 'res.partner':
            nom_objet = 'partenaire'           # Libellé pour affichage dans message information/erreur
            champ_primaire = 'ref'             # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
            champ_reference = 'ref'            # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
            # 2 champs suivants : on récupère les id des types de compte comptable payable et recevable pour création comptes comptables clients et fournisseurs (généralement 411 et 401).
            res_model, data_account_type_receivable_id = self.env['ir.model.data'].get_object_reference('account','data_account_type_receivable')
            res_model, data_account_type_payable_id = self.env['ir.model.data'].get_object_reference('account','data_account_type_payable')
        elif model == 'of.service':
            nom_objet = 'service OpenFire'     # Libellé pour affichage dans message information/erreur
            champ_primaire = 'id'              # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
            champ_reference = ''               # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
        elif model == 'res.partner.bank':
            nom_objet = 'Comptes en banque partenaire'           # Libellé pour affichage dans message information/erreur
            champ_primaire = 'acc_number'             # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
            champ_reference = ''            # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
        elif model == 'crm.lead':
            nom_objet = u'partenaire/opportunité'   # Libellé pour affichage dans message information/erreur
            champ_primaire = 'of_ref'               # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
            champ_reference = 'of_ref'              # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant

        # Initialisation variables
        champs_odoo = self.get_champs_odoo(model) # On récupère la liste des champs de l'objet (depuis ir.model.fields)
        date_debut = time.strftime('%Y-%m-%d %H:%M:%S')

        if simuler:
            sortie_succes = sortie_avertissement = sortie_erreur = u"SIMULATION - Rien n'a été créé/modifié.\n"
        else:
            sortie_succes = sortie_avertissement = sortie_erreur = u""

        nb_total = 0
        nb_ajout = 0
        nb_maj = 0
        nb_echoue = 0
        erreur = 0

#
# LECTURE DU FICHIER D'IMPORT
#
        
        # Lecture du fichier d'import par la bibliothèque csv de python
        fichier = base64.decodestring(self.file)
        dialect = csv.Sniffer().sniff(fichier) # Deviner automatiquement les paramètres : caractère séparateur, type de saut de ligne, ...
        fichier = StringIO(fichier)
 
        # On prend le séparateur indiqué dans le formulaire si est renseigné.
        # Sinon on prend celui deviné par la bibliothèque csv, et si vierge, on prend le ; par défaut.

        if self.separateur and self.separateur.strip(' '):
            dialect.delimiter = str(self.separateur.strip(' ').replace('\\t', '\t'))
        else:
            if dialect.delimiter and dialect.delimiter.strip(' '):
                self.separateur = dialect.delimiter.replace('\t', '\\t')
            else:
                self.separateur = dialect.delimiter = ';'

#
# ANALYSE DES CHAMPS DU FICHIER D'IMPORT
#

        # On récupère la 1ère ligne du fichier (liste des champs) pour vérifier si des champs existent en plusieurs exemplaires
        ligne = fichier.readline().strip().decode('utf8', 'ignore').split(dialect.delimiter) # Liste des champs de la 1ère ligne du fichier d'import

        # Vérification si le champ primaire est bien dans le fichier d'import (si le champ primaire est défini)
        if champ_primaire and champ_primaire not in ligne:
            erreur = 1
            sortie_erreur += u"Le champ référence qui permet d'identifier un %s (%s) n'est pas dans le fichier d'import.\n" % (nom_objet, champ_primaire)

        # Vérification si il y a des champs du fichier d'import qui sont en plusieurs exemplaires
        # et détection champ relation (id, id externe, nom)
        doublons = {}
        for champ_fichier in ligne:
            champ_fichier = champ_fichier.strip(dialect.quotechar) # On enlève les séparateurs de texte (souvent guillemet ou apostrophe) aux extrimités de la chaine.

            # Récupération du champ relation si est indiqué (dans le nom du champ après un /)
            champ_relation = champ_fichier[champ_fichier.rfind('/')+1 or len(champ_fichier):].strip() # On le récupère.

            if champ_relation: # Si est défini, on le retire du nom du champ.
                champ_fichier = champ_fichier[0:champ_fichier.rfind('/') if champ_fichier.rfind('/') != -1  else len(champ_fichier)].strip()

            if champ_fichier in doublons:
                doublons[champ_fichier] = doublons[champ_fichier] + 1
            else:
                doublons[champ_fichier] = 1

            # Test si est un champ de l'objet (sinon message d'information que le champ est ignoré à l'import)
            if champ_fichier not in champs_odoo:
                sortie_avertissement += u"Info : colonne \"%s\" dans le fichier d'import non reconnue. Ignorée lors de l'import.\n" % champ_fichier
            else:
                # Vérification que le champ relation (si est indiqué) est correct.
                if champ_relation and champs_odoo[champ_fichier]['type'] in ('many2one') and not champs_odoo[champ_fichier]['relation_champ']:
                    if not self.env['ir.model.fields'].search(['&',('model','=', model),('name','=',champ_relation)]):
                        sortie_erreur += u"Le champ relation \"%s\" (après le /) de la colonne \"%s\" n'existe pas.\n" % (champ_relation, champ_fichier)
                        erreur = 1
                    else:
                        champs_odoo[champ_fichier]['relation_champ'] = champ_relation
                elif champ_relation:
                    sortie_erreur += u"Un champ relation (après le /) dans la colonne \"%s\" n'est pas possible pour ce champ.\n" % champ_fichier
                    erreur = 1

        for champ_fichier in doublons:
            # On affiche un message d'avertissement si le champ existe en plusieurs exemplaires et si c'est un champ connu à importer
            if champ_fichier in champs_odoo and doublons[champ_fichier] > 1:
                sortie_erreur += u"La colonne \"%s\" dans le fichier d'import existe en %s exemplaires.\n" % (champ_fichier, doublons[champ_fichier])
                erreur = 1

        if erreur: # On arrête si erreur
            self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})
            return

        # On ajoute le séparateur (caractère souligné) entre le préfixe et la référence si il n'a pas déjà été mis.
        prefixe = self.prefixe and self.prefixe.encode("utf-8") or ''
        if prefixe and prefixe[-1:] != '_':
            prefixe = prefixe + '_'

        fichier.seek(0, 0) # On remet le pointeur au début du fichier
        fichier = csv.DictReader(fichier, dialect = dialect) # Renvoi une liste de dictionnaires avec le nom du champ_fichier comme clé

        doublons = {} # Variable pour test si enregistrement en plusieurs exemplaires dans fichier d'import
        i = 1 # No de ligne

#
# IMPORT ENREGISTREMENT PAR ENREGISTREMENT
#

        # On parcourt le fichier enregistrement par enregistrement
        for ligne in fichier:
            ligne = {key.decode('utf8', 'ignore'):value.decode('utf8', 'ignore') for key, value in ligne.iteritems()}
            i = i + 1
            nb_total = nb_total + 1
            erreur = 0

            # On rajoute le préfixe devant la valeur du champ référence de l'objet (si existe).
            if champ_reference and champ_reference in ligne:
                ligne[champ_reference] =  prefixe + ligne[champ_reference]

    #
    # PARCOURS DE TOUS LES CHAMPS DE L'ENREGISTREMENT
    #

            valeurs = {} # Variables qui récupère la valeur des champs à importer (pour injection à fonction create ou update)

            # Parcours de tous les champs de la ligne
            for champ_fichier in ligne:

                # Pour import articles, champ price est le coût d'achat à mettre dans le prix fournisseur.
                # On l'ignore car sera récupéré avec le champ seller_ids (fournisseur), voir plus bas.
                if model == 'product.template' and champ_fichier == 'price':
                        continue

                # Si le nom du champ contient un champ relation c'est à dire se terminant par /nom_du_champ on l'enlève. 
                champ_fichier_sansrel = champ_fichier[0:champ_fichier.rfind('/') if champ_fichier.rfind('/') != -1  else len(champ_fichier)].strip()

                if champ_fichier_sansrel in champs_odoo: # On ne récupère que les champs du fichier d'import qui sont des champs de l'objet (on ignore les champs inconnus du fichier d'import).
                    # Valeur du champ : suppression des espaces avant et après et conversion en utf8.
                    ligne[champ_fichier] = ligne[champ_fichier].strip()

                    if ligne[champ_fichier].strip().lower() == "#vide":
                        ligne[champ_fichier] = "#vide"

        #
        # VÉRIFICATION DE L'INTÉGRITÉ DE LA VALEUR DES CHAMPS
        # POUR LES CRITÈRES QUI NE DÉPENDENT PAS DU TYPE DU CHAMP
        #

                    # si le champs est requis, vérification qu'il est renseigné
                    if champs_odoo[champ_fichier_sansrel]['requis'] and (ligne[champ_fichier] == "" or ligne[champ_fichier] == "#vide"):
                        sortie_erreur += u"Ligne %s : champ %s (%s) vide alors que requis. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, nom_objet.capitalize())
                        erreur = 1

                    # Si le champ relation est un id, vérification qu'est un entier
                    if champs_odoo[champ_fichier_sansrel]['relation_champ'] == 'id':
                        try:
                            int(ligne[champ_fichier])
                        except ValueError:
                            sortie_erreur += u"Ligne %s : champ %s (%s) n'est pas un id (nombre entier) alors que le champ relation (après le /) est un id. %s non importé.\n" % (i,  champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, nom_objet.capitalize())
                            erreur = 1
                            continue

        #
        # FORMATAGE ET VÉRIFICATION DE L'INTÉGRITÉ DE LA VALEUR DES CHAMPS
        # POUR LES CRITÈRES QUI DÉPENDENT DU TYPE DU CHAMP
        #

                    # Si est un float
                    if champs_odoo[champ_fichier_sansrel]['type'] == 'float':
                        ligne[champ_fichier] = ligne[champ_fichier].replace(',', '.')
                        try:
                            float(ligne[champ_fichier])
                            valeurs[champ_fichier_sansrel] = ligne[champ_fichier]
                        except ValueError:
                            sortie_erreur += u"Ligne %s : champ %s (%s) n'est pas un nombre. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier_sansrel, nom_objet.capitalize())
                            erreur = 1

                    # Si est un field selection
                    elif champs_odoo[champ_fichier_sansrel]['type'] == 'selection':
                        # C'est un champ sélection. On vérifie que les données sont autorisées.
                        if ligne[champ_fichier] not in dict(self.env[model]._fields[champ_fichier].selection):
                            sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" non autorisée. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], nom_objet.capitalize())
                            erreur = 1
                        else:
                            valeurs[champ_fichier_sansrel] = ligne[champ_fichier]

                    # Si est un boolean
                    elif champs_odoo[champ_fichier_sansrel]['type'] == 'boolean':
                        if ligne[champ_fichier].upper() in ('1', "TRUE", "VRAI"):
                            ligne[champ_fichier] = True
                        elif ligne[champ_fichier].upper() in ('0', "FALSE", "FAUX"):
                            ligne[champ_fichier] = False
                        else:
                            sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" non autorisée (admis 0, 1, True, False, vrai, faux). %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], nom_objet.capitalize())
                            erreur = 1

                    # si est un many2one
                    elif champs_odoo[champ_fichier_sansrel]['type'] == 'many2one':
                        if ligne[champ_fichier] == "#vide" and not champs_odoo[champ_fichier_sansrel]['requis']:
                            # Si le champ n'est pas obligatoire et qu'il est vide, on met une valeur vide.
                            valeurs[champ_fichier_sansrel] = ""
                        elif ligne[champ_fichier] != "":
                            # Si import partenaires et si c'est le compte comptable client ou fournisseur, on regarde si pointe sur un compte comptable existant
                            if model == 'res.partner' and champ_fichier == 'property_account_receivable_id':
                                res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search(['&',('code', '=', ligne[champ_fichier]), ('internal_type', '=', 'receivable')])
                            elif model == 'res.partner' and champ_fichier == 'property_account_payable_id':
                                res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search(['&',('code', '=', ligne[champ_fichier]), ('internal_type', '=', 'payable')])
                            else:
                                if ligne[champ_fichier] == "#vide":
                                    res_ids = ""
                                else:
                                    res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search([(champs_odoo[champ_fichier_sansrel]['relation_champ'] or 'name', '=', ligne[champ_fichier])])

                            if len(res_ids) == 1:
                                valeurs[champ_fichier_sansrel] = res_ids.id
                            elif len(res_ids) > 1:
                                sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" a plusieurs correspondances. %s non importé.\n", (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], nom_objet.capitalize())
                                erreur = 1
                            else:
                                # Si import de partenaires et champ compte comptable (client et fournisseur), on le créer.
                                if model == 'res.partner' and champ_fichier == 'property_account_receivable_id' and 'name' in ligne:
                                    if not simuler:
                                        valeurs[champ_fichier_sansrel] = self.env[champs_odoo[champ_fichier_sansrel]['relation']].create({'name': ligne['name'], 'code': ligne[champ_fichier], 'reconcile': True, 'user_type_id': data_account_type_receivable_id})
                                elif model == 'res.partner' and champ_fichier == 'property_account_payable_id' and 'name' in ligne:
                                    if not simuler:
                                        valeurs[champ_fichier_sansrel] = self.env[champs_odoo[champ_fichier_sansrel]['relation']].create({'name': ligne['name'], 'code': ligne[champ_fichier], 'reconcile': True, 'user_type_id': data_account_type_payable_id})
                                elif ligne[champ_fichier] == "#vide":
                                    valeurs[champ_fichier_sansrel] = ''
                                else:
                                    sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" n'a pas de correspondance. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier], nom_objet.capitalize())
                                    erreur = 1

                    # Si est un one2many
                    elif champs_odoo[champ_fichier_sansrel]['type'] == 'one2many':
                        # Cas des fournisseurs pour les produits. Il y a un objet intermédiaire avec un enregistrement pour chaque produit.
                        # On crée le fournisseur dans cet objet en renseignant le prix d'achat
                        if model == 'product.template' and champ_fichier == 'seller_ids':
                            res_ids = self.env['res.partner'].search(['&',('name', '=', ligne[champ_fichier]),('supplier', '=', True)])
                            if len(res_ids) == 1:
                                if 'price' in ligne:
                                    valeurs[champ_fichier_sansrel] = [(5, ), (0, 0, {'name': res_ids.id, 'price': ligne['price'].replace(',', '.')})]
                                else:
                                    valeurs[champ_fichier_sansrel] = [(5, ), (0, 0, {'name': res_ids.id})]
                            elif len(res_ids) > 1:
                                sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" a plusieurs correspondances. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier].strip(), nom_objet.capitalize())
                                erreur = 1
                            else:
                                sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" n'a pas de correspondance. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, ligne[champ_fichier].strip(), nom_objet.capitalize())
                                erreur = 1

                    # Si est un many2many
                    elif champs_odoo[champ_fichier_sansrel]['type'] == 'many2many':
                        # C'est un many2many
                        # Ça équivaut à des étiquettes. On peut en importer plusieurs en les séparant par des virgules.
                        # Ex : étiquette1, étiquette2, étiquette3 
                        tag_ids = []
                        if ligne[champ_fichier] and ligne[champ_fichier] != "#vide": # S'il y a des données dans le champ d'import
                            ligne[champ_fichier] = ligne[champ_fichier].split(',') # On sépare les étiquettes quand il y a une virgule
                            for tag in ligne[champ_fichier]: # On parcourt les étiquettes à importer
                                # On regarde si elle existe.
                                res_ids = self.env[champs_odoo[champ_fichier_sansrel]['relation']].with_context(active_test=False).search([(champs_odoo[champ_fichier_sansrel]['relation_champ'] or 'name', '=', tag.strip())])
                                if len(res_ids) == 1:
                                    tag_ids.append(res_ids.id)
                                elif len(res_ids) > 1:
                                    sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" a plusieurs correspondances. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, tag.strip(), nom_objet.capitalize())
                                    erreur = 1
                                else:
                                    sortie_erreur += u"Ligne %s : champ %s (%s) valeur \"%s\" n'a pas de correspondance. %s non importé.\n" % (i, champs_odoo[champ_fichier_sansrel]['description'], champ_fichier, tag.strip(), nom_objet.capitalize())
                                    erreur = 1
                        if not erreur:
                            if ligne[champ_fichier] == "#vide":
                                valeurs[champ_fichier_sansrel] = [(5,)]
                            elif ligne[champ_fichier]:
                                valeurs[champ_fichier_sansrel] = [(6, 0, tag_ids)]

                    # Pour tous les autres types de champ (char, text, date, ...)
                    # On ne fait que prendre sa valeur sans traitement particulier
                    else:
                        if ligne[champ_fichier] == "#vide":
                            valeurs[champ_fichier_sansrel] = ''
                        elif ligne[champ_fichier] != '':
                            valeurs[champ_fichier_sansrel] = ligne[champ_fichier]

            if erreur: # On n'enregistre pas si erreur.
                nb_echoue = nb_echoue + 1
                continue

            # On regarde si l'enregistrement a déjà été importé (réf. en plusieurs exemplaires dans le fichier d'import).
            # Si c'est le cas, on l'ignore.
            if champ_primaire:
                if ligne[champ_primaire] in doublons:
                    doublons[ligne[champ_primaire]][0] = doublons[ligne[champ_primaire]][0] + 1
                    doublons[ligne[champ_primaire]][1] = doublons[ligne[champ_primaire]][1] + ", " + str(i)
                    nb_echoue = nb_echoue + 1
                    continue
                else:
                    doublons[ligne[champ_primaire]] = [1, str(i)]

                # On regarde si l'enregistrement existe déjà dans la base
                res_objet_ids = model_obj.with_context(active_test=False).search([(champ_primaire,'=', ligne[champ_primaire])])
            else:
                res_objet_ids = "" # Si le champ primaire n'est pas défini, on ne fait que des créations.

            libelle_ref = u"réf. " + ligne[champ_reference] if champ_reference else ligne[champ_primaire] if champ_primaire else ligne['name'] if 'name' in ligne else ''

            if not res_objet_ids:
                # L'enregistrement n'existe pas dans la base, on l'importe (création)
                # Mais en cas de création, on doit vérifier que tous les champs Odoo requis ont bien été renseignés.
                for cle in champs_odoo:
                    if champs_odoo[cle]['requis'] == True and cle not in valeurs:
                        sortie_erreur += u"Ligne %s : champ %s (%s) obligatoire mais non présent dans le fichier d'import. %s non importé.\n" % (i, champs_odoo[cle]['description'], cle, nom_objet.capitalize())
                        erreur = 1

                if erreur: # On n'enregistre pas si erreur.
                    nb_echoue = nb_echoue + 1
                    continue

                try:
                    if not simuler:
                        model_obj.create(valeurs)
                    nb_ajout = nb_ajout + 1
                    sortie_succes += u"Création %s %s (ligne %s)\n" % (nom_objet, libelle_ref, i)
                except Exception, exp:
                    sortie_erreur += u"Ligne %s : échec création %s %s - Erreur : %s\n" % (i, nom_objet, libelle_ref, exp)
                    nb_echoue = nb_echoue + 1

            elif len(res_objet_ids) == 1:
                # Il a un (et un seul) enregistrement dans la base avec cette référence. On le met à jour.
                try:
                    if not simuler:
                        res_objet_ids.write(valeurs)
                    nb_maj = nb_maj + 1
                    sortie_succes += u"MAJ %s %s (ligne %s)\n" % (nom_objet, libelle_ref, i)
                except Exception, exp:
                    sortie_erreur += u"Ligne %s : échec mise à jour %s %s - Erreur : %s\n" % (i, nom_objet, libelle_ref, exp)
                    nb_echoue = nb_echoue + 1

            else:
                # Il existe plusieurs articles dans la base avec cette référence. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                nb_echoue = nb_echoue + 1
                sortie_erreur += u"Ligne %s %s %s en plusieurs exemplaire dans la base, on ne sait pas lequel mettre à jour. %s non importé.\n" % (i, nom_objet, libelle_ref, nom_objet.capitalize())

            if not simuler:
                self._cr.commit()

            if nb_total % frequence_commit == 0:
                self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})

        # On affiche les enregistrements qui étaient en plusieurs exemplaires dans le fichier d'import.
        for cle in doublons:
            if doublons[cle][0] > 1:
                sortie_avertissement += u"%s réf. %s existe en %s exemplaires dans le fichier d'import (lignes %s). Seule la première ligne est importée.\n" % (nom_objet.capitalize(), cle, doublons[cle][0], doublons[cle][1])
        
        # On enregistre les dernières lignes qui ne l'auraient pas été.
        self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur, 'date_debut_import' : date_debut, 'date_fin_import' : time.strftime('%Y-%m-%d %H:%M:%S')})

        if not simuler:
            self.write({'state': 'importe'})

        self._cr.commit()

        return
