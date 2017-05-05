# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time, csv, base64
from StringIO import StringIO

class of_import(models.Model):
    _name = 'of.import'

    name = fields.Char('Nom', size=64, required=True)
    type_import = fields.Selection([('product.template', 'Article'), ('res.partner', 'Partenaire')], string="Type d'import", required=True)
    date = fields.Datetime('Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), help=u"Date qui sera affectée aux imports comme date de valeur.")
    date_debut_import = fields.Datetime('Début', readonly=True)
    date_fin_import = fields.Datetime('Fin', readonly=True)
    prefixe = fields.Char(u'Préfixe référence', size=10, help=u"Texte qui précèdera la référence.")
    user_id = fields.Many2one('res.users', 'Utilisateur', readonly=True, default=lambda self: self._uid)
    file = fields.Binary('Fichier', required=True)
    file_name = fields.Char('Nom du fichier')
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
        "Renvoit un dictionnaire contenant les caractéristiques des champs Odoo en fonction du type d'import sélectionné (champ type_import)"

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
                if champ in ('tz', 'lang'):
                    continue
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
        
        # Variables de configuration
        frequence_commit = 100 # Enregistrer (commit) tous les n enregistrements

        model = self.type_import # On récupère l'objet (model) à importer indiqué dans le champ type d'import
        model_obj = self.env[model]

        if model == 'product.template':
            nom_objet = 'article'              # Libellé pour affichage dans message information/erreur
            champ_primaire = 'default_code'    # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
            champ_reference = 'default_code'   # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
        elif model == 'res.partner':
            nom_objet = 'partenaire'              # Libellé pour affichage dans message information/erreur
            champ_primaire = 'ref'    # Champ sur lequel on se base pour détecter si enregistrement déjà existant (alors mise à jour) ou inexistant (création)
            champ_reference = 'ref'   # Champ qui contient la référence ( ex : référence du produit, d'un client, ...) pour ajout du préfixe devant
            res_model, data_account_type_receivable_id = self.env['ir.model.data'].get_object_reference('account','data_account_type_receivable')
            res_model, data_account_type_payable_id = self.env['ir.model.data'].get_object_reference('account','data_account_type_payable')

        champs_odoo = self.get_champs_odoo(model) # On récupère la liste des champs de l'objet (depuis ir.model.fields)
        date_debut = time.strftime('%Y-%m-%d %H:%M:%S')

        if simuler:
            sortie_succes = sortie_avertissement = sortie_erreur = u"SIMULATION - Rien n'a été créé/modifié.\n" 
        else:
            sortie_succes = ''
            sortie_avertissement = ''
            sortie_erreur = ''

        nb_total = 0
        nb_ajout = 0
        nb_maj = 0
        nb_echoue = 0
        erreur = 0
        
        # Lecture du fichier d'import par la bibliothèque csv de python
        fichier = base64.decodestring(self.file)
        dialect = csv.Sniffer().sniff(fichier) # Deviner automatiquement les paramètres : caractère séparateur, type de saut de ligne, ...
        fichier = StringIO(fichier)
 
        # On récupère la 1ère ligne du fichier (liste des champs) pour vérifier si des champs existent en plusieurs exemplaires
        ligne = fichier.readline().strip().split(dialect.delimiter) # Liste des champs de la 1ère ligne du fichier d'import

        # Vérification si le champ primaire est bien dans le fichier d'import
        if champ_primaire and champ_primaire not in ligne:
            erreur = 1
            sortie_erreur += u"Le champ référence qui permet d'identifier un " + nom_objet + " (" + champ_primaire + u") n'est pas dans le fichier d'import.\n"

        # Vérification si champs dans fichier d'import en plusieurs exemplaires
        doublons = {}
        for champ in ligne:
            champ = champ.strip(dialect.quotechar)
            if champ in doublons:
                doublons[champ] = doublons[champ] + 1
            else:
                doublons[champ] = 1
            # Test si est un champ de l'objet (sinon message d'information que le champ est ignoré à l'import)
            if champ not in champs_odoo:
                sortie_avertissement += u"Info : colonne \"" + champ.decode('utf8', 'ignore') + u"\" dans le fichier d'import non reconnue. Ignorée lors de l'import.\n"
            else:
                # Ajout de la source (id, id externe, nom)
                if champ.replace(' ', '').lower().endswith('/id'):
                    champs_odoo[champ]['source'] = 'id'
                elif champ.replace(' ', '').lower().endswith('/idexterne'):
                    champs_odoo[champ]['source'] = 'id externe'
                else:
                    champs_odoo[champ]['source'] = ''

        for champ in doublons:
            # On affiche un message d'avertissement si le champ existe en plusieurs exemplaires et si c'est un champ connu à importer
            if champ in champs_odoo and doublons[champ] > 1:
                sortie_erreur += "La colonne \"" + champ + u"\" dans le fichier d'import existe en " + str(doublons[champ]) + u" exemplaires.\n"
                erreur = 1

        if erreur: # On arrête si erreur
            self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})
            return

        # On ajoute le séparateur (caractère souligné) entre le préfixe et la référence si il n'a pas déjà été mis.
        prefixe = self.prefixe or ''
        if prefixe and prefixe[-1:] != '_':
            prefixe = self.prefixe + '_'

        fichier.seek(0, 0) # On remet le pointeur au début du fichier
        fichier = csv.DictReader(fichier, dialect = dialect) # Renvoit une liste de dictionnaires avec le nom du champ comme clé

        doublons = {} # Variable pour test si enregistrement en plusieurs exemplaires dans fichier d'import
        i = 1 # No de ligne

        # On parcourt le fichier enregistrement par enregistrement
        for ligne in fichier:
            i = i + 1
            nb_total = nb_total + 1
            erreur = 0

            # On rajoute le préfixe devant la valeur du champ référence de l'objet (si existe).
            if champ_reference and champ_reference in ligne:
                ligne[champ_reference] =  prefixe + ligne[champ_reference]

            # On vérifie le contenu des champs
            valeurs = {}
            for cle in ligne: # Parcours de tous les champs de la ligne
                if cle in champs_odoo: # On ne récupère que les champs du fichier d'import qui sont des champs de l'objet (on ignore les autres)
                    ligne[cle] = ligne[cle].strip() # Suppression des espaces avant et après

                    # Test si le champs est requis
                    if champs_odoo[cle]['requis'] and ligne[cle] == "":
                        sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") vide alors que requis. " + nom_objet.capitalize() + u" non importé.\n"
                        erreur = 1

                    # Si est un float
                    if champs_odoo[cle]['type'] == 'float':
                        ligne[cle] = ligne[cle].replace(',', '.')
                        try:
                            float(ligne[cle])
                        except ValueError:
                            sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") n'est pas un nombre. " + nom_objet.capitalize() + u" non importé.\n"
                            erreur = 1

                    if champs_odoo[cle]['type'] == 'selection':
                        # C'est un champ sélection. On vérifie que les données sont autorisées
                        if ligne[cle] not in dict(self.env[model]._fields[cle].selection):
                            sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(ligne[cle]) + u"\" non autorisée. " + nom_objet.capitalize() + u" non importé.\n"
                            erreur = 1

                    if champs_odoo[cle]['type'] == 'boolean':
                        if ligne[cle].upper() in ('1', "TRUE", "VRAI"):
                            ligne[cle] = True
                        elif ligne[cle].upper() in ('0', "FALSE", "FAUX"):
                            ligne[cle] = False
                        else:
                            sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(ligne[cle]) + u"\" non autorisée (admis 0, 1, True, False, vrai, faux). " + nom_objet.capitalize() + u" non importé.\n"
                            erreur = 1

                    if champs_odoo[cle]['type'] == 'many2one':
                        if model == 'res.partner' and cle == 'property_account_receivable_id':
                            res_ids = self.env[champs_odoo[cle]['relation']].with_context(active_test=False).search(['&',('code', '=', ligne[cle]), ('internal_type', '=', 'receivable')])
                        elif model == 'res.partner' and cle == 'property_account_payable_id':
                            res_ids = self.env[champs_odoo[cle]['relation']].with_context(active_test=False).search(['&',('code', '=', ligne[cle]), ('internal_type', '=', 'payable')])
                        else:
                            res_ids = self.env[champs_odoo[cle]['relation']].with_context(active_test=False).search([(champs_odoo[cle]['relation_champ'] or 'name', '=', ligne[cle])])

                        if len(res_ids) == 1:
                            valeurs[cle] = res_ids.id
                        elif len(res_ids) > 1:
                            sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(ligne[cle]) + u"\" a plusieurs correspondances. " + nom_objet.capitalize() + u" non importé.\n"
                            erreur = 1
                        else:
                            # si import de partenaires et champ compte comptable (client et fournisseur), on le créer
                            if model == 'res.partner' and cle == 'property_account_receivable_id' and 'name' in ligne:
                                if not simuler:
                                    valeurs[cle] = self.env[champs_odoo[cle]['relation']].create({'name': ligne['name'], 'code': ligne[cle], 'reconcile': True, 'user_type_id': data_account_type_receivable_id})
                            elif model == 'res.partner' and cle == 'property_account_payable_id' and 'name' in ligne:
                                if not simuler:
                                    valeurs[cle] = self.env[champs_odoo[cle]['relation']].create({'name': ligne['name'], 'code': ligne[cle], 'reconcile': True, 'user_type_id': data_account_type_payable_id})
                            else:
                                sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(ligne[cle]) + u"\" n'a pas de correspondance. " + nom_objet.capitalize() + u" non importé.\n"
                                erreur = 1
                    else:
                        valeurs[cle] = ligne[cle]

                    if champs_odoo[cle]['type'] == 'one2many':
                        if model == 'product.template' and cle == 'seller_ids':
                            res_ids = self.env['res.partner'].search(['&',('name', '=', ligne[cle]),('supplier', '=', True)])
                            if len(res_ids) == 1:
                                valeurs[cle] = [(5, ), (0, 0, {'name': res_ids.id})]
                            elif len(res_ids) > 1:
                                sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(ligne[cle]).strip() + u"\" a plusieurs correspondances. " + nom_objet.capitalize() + u" non importé.\n"
                                erreur = 1
                            else:
                                sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(ligne[cle]).strip() + u"\" n'a pas de correspondance. " + nom_objet.capitalize() + u" non importé.\n"
                                erreur = 1

                    if champs_odoo[cle]['type'] == 'many2many':
                        # C'est un many2many
                        # Ça équivaut à des étiquettes. On peut en importer plusieurs en les séparant par des virgules.
                        # Ex : étiquette1, étiquette2, étiquette3 
                        tag_ids = []
                        if ligne[cle]: # S'il y a des données dans le champ d'import
                            ligne[cle] = ligne[cle].split(',') # On sépare les étiquettes quand il y a une virgule
                            for tag in ligne[cle]: # On parcourt les étiquettes à importer
                                # On regarde si elle existe.
                                res_ids = self.env[champs_odoo[cle]['relation']].with_context(active_test=False).search([(champs_odoo[cle]['relation_champ'] or 'name', '=', tag.strip())])
                                if len(res_ids) == 1:
                                    tag_ids.append(res_ids.id)
                                elif len(res_ids) > 1:
                                    sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(tag).strip() + u"\" a plusieurs correspondances. " + nom_objet.capitalize() + u" non importé.\n"
                                    erreur = 1
                                else:
                                    sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") valeur \"" + str(tag).strip() + u"\" n'a pas de correspondance. " + nom_objet.capitalize() + u" non importé.\n"
                                    erreur = 1
                        if not erreur:
                            valeurs[cle] = [(6, 0, tag_ids)]

            if erreur: # On n'enregistre pas si erreur.
                nb_echoue = nb_echoue + 1
                continue

            # On regarde si l'enregistrement a déjà été importé (réf. en plusieurs exemplaires dans le fichier d'import).
            # Si c'est le cas, on l'ignore.
            if ligne[champ_primaire] in doublons:
                doublons[ligne[champ_primaire]][0] = doublons[ligne[champ_primaire]][0] + 1
                doublons[ligne[champ_primaire]][1] = doublons[ligne[champ_primaire]][1] + ", " + str(i)
                nb_echoue = nb_echoue + 1
                continue
            else:
                doublons[ligne[champ_primaire]] = [1, str(i)]

            # On regarde si l'enregistrement existe déjà dans la base
            res_objet_ids = model_obj.search([(champ_primaire,'=', ligne[champ_primaire]),'|',('active', '=', True),('active', '=', False)])

            if not res_objet_ids:
                # L'enregistrement n'existe pas dans la base, on l'importe (création)
                # Mais en cas de création, on doit vérifier que tous les champs Odoo requis ont bien été renseignés.
                for cle in champs_odoo:
                    if champs_odoo[cle]['requis'] == True and cle not in valeurs:
                        sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") obligatoire mais non présent dans le fichier d'import. " + nom_objet.capitalize() + u" non importé.\n"
                        erreur = 1

                if erreur: # On n'enregistre pas si erreur.
                    nb_echoue = nb_echoue + 1
                    continue

                try:
                    if not simuler:
                        model_obj.create(valeurs)
                    sortie_succes += u"Création " + nom_objet + u" réf. " + (ligne[champ_reference] or ligne[champ_primaire]) + " (ligne " + str(i) + ")\n"
                    nb_ajout = nb_ajout = + 1
                except Exception, exp:
                    sortie_erreur += "Ligne " + str(i) + u" : échec création " + nom_objet + u" réf. " + (ligne[champ_reference] or ligne[champ_primaire]) + " - Erreur : " + str(exp) + "\n"
                    nb_echoue = nb_echoue + 1

            elif len(res_objet_ids) == 1:
                # Il a un (et un seul) enregistrement dans la base avec cette référence. On le met à jour.
                try:
                    if not simuler:
                        res_objet_ids.write(valeurs)
                    sortie_succes += u"MAJ " + nom_objet +  u" réf. " + (ligne[champ_reference] or ligne[champ_primaire]) + " (ligne " + str(i) + ")\n"
                    nb_maj = nb_maj + 1
                except Exception, exp:
                    sortie_erreur += "Ligne " + str(i) + u" : échec mise à jour " + nom_objet + u" réf. " + (ligne[champ_reference] or ligne[champ_primaire]) + " - Erreur : " + str(exp) + "\n"
                    nb_echoue = nb_echoue + 1

            else:
                # Il existe plusieurs articles dans la base avec cette référence. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                sortie_erreur += "Ligne " + str(i) + " " + nom_objet + u" réf. " + (ligne[champ_reference] or ligne[champ_primaire]) + u" en plusieurs exemplaire dans la base, on ne sait pas lequel mettre à jour. " + nom_objet.capitalize() + u" non importé.\n"
                nb_echoue = nb_echoue + 1

            if nb_total % frequence_commit == 0:
                self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})
                self._cr.commit()

        # On affiche les enregistrements qui étaient en plusieurs exemplaires dans le fichier d'import.
        for cle in doublons:
            if doublons[cle][0] > 1:
                sortie_avertissement += nom_objet.capitalize() + u" réf. " + cle.decode('utf8', 'ignore') + u" existe en " + str(doublons[cle][0]) + u" exemplaires dans le fichier d'import (lignes " + doublons[cle][1] + u"). Seule la première ligne est importée.\n"
        
        # On enregistre les dernières lignes qui ne l'auraient pas été.
        self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur, 'date_debut_import' : date_debut, 'date_fin_import' : time.strftime('%Y-%m-%d %H:%M:%S')})
        if not simuler:
            self.write({'state': 'importe'})
        self._cr.commit()

        return
