# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time, csv, base64
from StringIO import StringIO

class of_import(models.Model):
    _name = 'of.import'

    name = fields.Char('Nom', size=64, required=True)
    date_import = fields.Datetime('Date', required=True, readonly=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    prefixe = fields.Char(u'Préfixe référence article', size=10, help=u"Texte qui précèdera la référence des articles.")
    debut = fields.Datetime(u'Début', readonly=True)
    fin = fields.Datetime('Fin', readonly=True)
    duree = fields.Char(u'Durée', compute="_calcul_duree", size=16, readonly=True, store=True)
    user_id = fields.Many2one('res.users', 'Utilisateur', readonly=True, default=lambda self: self._uid)
    file = fields.Binary('Fichier', required=True)
    file_name = fields.Char('Nom du fichier')
    state = fields.Selection([('brouillon', 'Brouillon'), ('importe', 'Importé'), ('annule', 'Annulé')], 'État', default='brouillon', readonly=True)
    nb_total = fields.Integer('Nombre total', readonly=True)
    nb_ajout = fields.Integer(u'Ajoutés', readonly=True)
    nb_maj = fields.Integer(u'Mis à jour', readonly=True)
    nb_echoue = fields.Integer(u'Échoués/ignorés', readonly=True)
    sortie_succes = fields.Text('Information', readonly=True)
    sortie_avertissement = fields.Text('Avertissements', readonly=True)
    sortie_erreur = fields.Text('Erreurs', readonly=True)
    type = fields.Char(u'Type import', readonly=True, default='produit')

#     _defaults = {
#         'date_import': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
#         'state': 'brouillon',
#         'user_id': lambda obj, cr, uid, context: uid,
#         'type': 'produit'
#     }
    
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
        
        champs_odoo = {}
        champs_odoo['name'] = {'description': u'Nom du produit', 'requis': True, 'type': 'text', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['default_code'] = {'description': u'Référence produit', 'requis': True, 'type': 'text', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['list_price'] = {'description': u'Prix de vente', 'requis': True, 'type': 'float', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['standard_price2'] = {'description': u"Prix d'achat", 'requis': False, 'type': 'float', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['of_frais_port'] = {'description': u'Frais de port', 'requis': False, 'type': 'float', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['type'] = {'description': u'Type de produit', 'requis': False, 'type': 'text', 'res_model': '', 'champ_res_model': '', 'valeurs': ('consu', 'service', 'product')} 
        champs_odoo['sale_ok'] = {'description': u'Peut être vendu', 'requis': False, 'type': 'bool', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['purchase_ok'] = {'description': u'Peut être acheté', 'requis': False, 'type': 'bool', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['weight'] = {'description': u'Poids', 'requis': False, 'type': 'float', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['volume'] = {'description': u'Volume', 'requis': False, 'type': 'float', 'res_model': '', 'champ_res_model': ''}
        champs_odoo['barcode'] = {'description': u'Code barre', 'requis': False, 'type': 'text', 'res_model': '', 'champ_res_model': ''} 
        champs_odoo['uom_id'] = {'description': u'Unité de mesure', 'requis': False, 'type': 'one2many', 'res_model': 'product.uom', 'champ_res_model': 'name'}
        champs_odoo['uom_po_id'] = {'description': u"Unité de mesure d'achat", 'requis': False, 'type': 'one2many', 'res_model': 'product.uom', 'champ_res_model': 'name'}
        #route_ids
        #categ_id

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
        dialect = csv.Sniffer().sniff(fichier) # Deviner les paramètres : caractère séparateur, type de saut de ligne, ...
        fichier = StringIO(fichier)
 
        # On vérifie si les champs dans le fichier d'import existent en plusieurs exemplaires
        ligne = fichier.readline().strip().split(dialect.delimiter) # Liste des champs de la 1ère ligne du fichier d'import
        doublons = {}
        for champ in ligne:
            champ = champ.strip(dialect.quotechar)
            if champ in doublons:
                doublons[champ] = doublons[champ] + 1
            else:
                doublons[champ] = 1
        for champ in doublons:
            # On affiche un message d'avertissement si le champ existe en plusieurs exemplaires et si c'est un champ connu à importer
            if champ in champs_odoo and doublons[champ] > 1:
                sortie_erreur += "La colonne " + champ + u" du fichier d'import existe en " + str(doublons[champ]) + u" exemplaires.\n"
                erreur = 1

        if erreur: # On arrête si erreur
            self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})
            return

        fichier.seek(0, 0) # On remet le pointeur au début du fichier
        fichier = csv.DictReader(fichier, dialect = dialect) # Renvoit une liste de dictionnaires avec le nom du champ comme clé
        #reader = csv.reader(b, dialect)#, delimiter='\t')

        # On ajoute le séparateur entre le préfixe et la référence produit si il n'a pas déjà été mis.
        prefixe = self.prefixe or ''
        if prefixe and prefixe[-1:] != '_':
            prefixe = self.prefixe + '_'

        product_obj = self.env['product.template']
        doublons = {}
        i = 1 # No de ligne
        # On parcourt le fichier produit par produit
        for ligne in fichier:
            i = i + 1
            nb_total = nb_total + 1
            erreur = 0
            
            # Si on lit la 1ère ligne, on récupère le nom des champs du fichier d'import pour vérifier la validité des champs
            if nb_total == 1:
                for cle in champs_odoo:
                    # On vérifie que si le champ est requis, qu'il est dans le fichier d'import
                    if champs_odoo[cle]['requis'] == True and cle not in ligne:
                        erreur = 1
                        sortie_erreur += "Champ obligatoire " + cle.decode('utf8', 'ignore') + " (" + champs_odoo[cle]['description'] + u") non présent dans le fichier d'import\n"
                        
            if erreur: # On arrête si erreur
                self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})
                return

            # On rajoute le préfixe devant la référence du produit.
            if 'default_code' in ligne:
                ligne['default_code'] =  prefixe + ligne['default_code']

            # On vérifie le contenu des champs
            valeurs = {}
            for cle in ligne: # Parcours de tous les champs de la ligne
                if cle in champs_odoo: # On ne récupère que les champs du fichier d'import qui sont des champs de product.template (on ignore les autres)
                    ligne[cle] = ligne[cle].strip()
                    # Teste si le champs est requis
                    if champs_odoo[cle]['requis'] and ligne[cle] == "":
                        sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") vide alors que requis. Produit non importé.\n"
                        erreur = 1
                    # Teste si est un float correct
                    if champs_odoo[cle]['type'] == 'float':
                        ligne[cle] = ligne[cle].replace(',', '.')
                        try:
                            float(ligne[cle])
                        except ValueError:
                            sortie_erreur += "Ligne " + str(i) + u" : champ " + champs_odoo[cle]['description'] + " (" + cle.decode('utf8', 'ignore') + u") n'est pas un nombre. Produit non importé.\n"
                            erreur = 1
                            
                    valeurs[cle] = ligne[cle]

                elif nb_total == 1: # Si on est lors de la 1ère ligne
                    sortie_avertissement += u"Info : colonne " + cle.decode('utf8', 'ignore') + u" du fichier d'import non reconnue. Ignorée lors de l'import.\n"

            if erreur: # On n'enregistre pas si erreur.
                nb_echoue = nb_echoue + 1
                continue

            # On regarde si le produit a déjà été importé (réf. produit en plusieurs exemplaires dans le fichier d'import).
            # Si c'est le cas, on l'ignore.
            if ligne['default_code'] in doublons:
                doublons[ligne['default_code']][0] = doublons[ligne['default_code']][0] + 1
                doublons[ligne['default_code']][1] = doublons[ligne['default_code']][1] + ", " + str(i)
                nb_echoue = nb_echoue + 1
                continue
            else:
                doublons[ligne['default_code']] = [1, str(i)]

            # On regarde si le produit existe dans la base
            res_product_ids = product_obj.search([('default_code','ilike', ligne['default_code']),'|',('active', '=', True),('active', '=', False)])

            if not res_product_ids:
                # Le produit n'existe pas dans la base, on l'importe (création)
                try:
                    if not simuler:
                        product_obj.create(valeurs)
                    nb_ajout = nb_ajout = + 1
                    sortie_succes += u"Création produit réf. " + ligne['default_code'] + " (ligne " + str(i) + ")\n"
                except Exception, exp:
                    sortie_erreur += "Ligne " + str(i) + u" : échec création produit réf. " + ligne['default_code'] + " - Erreur : " + str(exp) + "\n"
                    nb_echoue = nb_echoue + 1
                    
            elif len(res_product_ids) == 1:
                # Il a un (et un seul) article dans Odoo avec cette référence. On le met à jour.
                if not simuler:
                    res_product_ids.write(valeurs)
                sortie_succes += u"MAJ produit réf. " + ligne['default_code'] + " (ligne " + str(i) + ")\n"
                nb_maj = nb_maj + 1
            else:
                # Il existe plusieurs articles dans Odoo avec cette référence. On ne sait pas lequel mettre à jour. On passe au suivant en générant une erreur.
                sortie_erreur += "Ligne " + str(i) + u" : réf. produit " + ligne['default_code'] + u" en plusieurs exemplaire dans la base, on ne sait pas lequel mettre à jour. Produit non importé.\n"
                nb_echoue = nb_echoue + 1
            
            if nb_total % frequence_commit == 0:
                self._cr.commit()
                self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})

        # On affiche les produits qui étaient en plusieurs exemplaires dans le fichier d'import.
        for cle in doublons:
            if doublons[cle][0] > 1:
                sortie_avertissement += u"Produit réf. " + cle.decode('utf8', 'ignore') + u" existe en " + str(doublons[cle][0]) + u" exemplaires dans le fichier d'import (lignes " + doublons[cle][1] + u"). Seule la première ligne est importée.\n"
        
        # On enregistre les dernières lignes qui ne l'auraient pas été.
        self.write({'nb_total': nb_total, 'nb_ajout': nb_ajout, 'nb_maj': nb_maj, 'nb_echoue': nb_echoue, 'sortie_succes': sortie_succes, 'sortie_avertissement': sortie_avertissement, 'sortie_erreur': sortie_erreur})
        self._cr.commit()

        return
