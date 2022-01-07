# -*- coding: utf-8 -*-

{
    'name': "OpenFire / Base",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': '',
    'complexity': "easy",
    'description': u"""
Personnalisation des fonctions de base Odoo :

- Ajout des colonnes destinataire et partenaire dans la vue liste des emails
- Ajout onglet historique dans formulaire partenaire
- Ajoute la référence du produit dans la vue liste
- Retire la couleur de fond aléatoire de l'image mise par défaut à la création d'un partenaire
- Ajoute le groupe utilisateur "Intranet"
- Affiche l'adresse du contact dans le menu déroulant de sélection d'un partenaire
- Affiche l'adresse au format français par défaut quand le pays n'est pas renseigné et non le format US
- Ajout de la recherche multi-mots pour les articles
- Désactive l'envoi des notifications par courriel des changements d'affectation des commandes et factures
- Restreint l'accès au menu "Applications" à l'utilisateur administrateur
- Soumet la désinstallation de module à une validation par mot de passe.
  Le hash du mot de passe doit être placé dans le fichier de configuration sous le nom 'of_module_uninstall_password'.

  Calcul du hash en python :

  from passlib.context import CryptContext; CryptContext(['pbkdf2_sha512']).encrypt("mon_mot_de_passe")
- API fonction permettant d'afficher un message dans une fenêtre au cours de l'exécution d'une fonction
- Ajout d'un champ calculé et d'un bouton sur les actions d'envoi de mail pour avoir une pré-visualisation du mail
- Permet à l'auteur d'un mail de le recevoir en copie (par défaut odoo retire l'expéditeur de la liste des destinataires)
- Nouvelle gestion des numéros de téléphone des partenaires avec formatage automatique des numéros
    -> Librairie Python phonenumbers nécessaire, pour installer : pip install phonenumbers

Ajout d'un modèle servant de log interne :
------------------------------------------
 - Titre : Généralement lié au nom du module.
 - Type d'erreur : Si erreur de validation par un connecteur alors catégorie de l'erreur (si présente) autrement définie par le développeur.
 - Modèle : Modèle dans lequel l'erreur s'est produite.
 - Fonction : Fonction dans laquelle l'erreur s'est produite.
 - Message : Si erreur de validation par un connecteur alors message retourné par l'erreur (si présent) autrement défini par le développeur.
 - Niveau de log : Peut être Info, Avertissement ou Erreur.
""",
    'website': "www.openfire.fr",
    'depends': [
        'base_iban',
        'base_vat',
        'crm',
        'product',
        'mail',
        'contacts'
    ],
    'category': "OpenFire",
    'data': [
        'data/report_paperformat.xml',
        'data/of_base_data.xml',
        'security/of_base_security.xml',
        'security/of_group_intranet_security.xml',
        'security/ir.model.access.csv',
        'views/of_base_view.xml',
        'views/of_log_message_views.xml',
        'views/templates.xml',
        'wizard/base_module_upgrade_view.xml',
        'wizard/of_popup_wizard_view.xml',
        'wizard/of_res_partner_check_duplications_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
