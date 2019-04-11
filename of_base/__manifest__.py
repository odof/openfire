# -*- coding: utf-8 -*-

{
    'name' : "OpenFire / Base",
    'version' : "10.0",
    'author' : "OpenFire",
    'license': '',
    'complexity': "easy",
    'description' : """
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
- API fonction permettant d'afficher un message dans une fenêtre au cours de l'exécution d'une fonction
- Ajout d'un champ calculé et d'un bouton sur les actions d'envoi de mail pour avoir une pré-visualisation du mail
- Permet à l'auteur d'un mail de le recevoir en copie (par défaut odoo retire l'expéditeur de la liste des destinataires)
""",
    'website' : "www.openfire.fr",
    'depends' : ["product", "mail"],
    'category' : "OpenFire",
    'data' : [
        'data/report_paperformat.xml',
        'security/of_group_intranet_security.xml',
        'views/of_base_view.xml',
        'wizard/wizard_change_active_product.xml',
        'wizard/of_popup_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
