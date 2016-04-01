# -*- coding: utf-8 -*-

{
    "name" : "OpenFire Base",
    "version" : "1.1",
    "author" : "OpenFire",
    'complexity': "easy",
    "description" : """
Personnalisations des fonctions de base Odoo :

- Ajout des colonnes destinataire et partenaire dans la vue liste des emails
- Ajout onglet historique dans formulaire partenaire
- Ajoute la référence du produit dans la vue liste
- Retire la couleur de fond aléatoire de l'image mise par défaut à la création d'un partenaire
- Ajoute le groupe utilisateur "Intranet"
- Affiche l'adresse du contact dans le menu déroulant de sélection d'un partenaire
- Affiche l'adresse au format français par défaut quand le pays n'est pas renseigné et non le format US
""",
    "website" : "www.openfire.fr",
    "depends" : ["product"], # Migration 8 vers 9 "email_template",
    "category" : "OpenFire",
    "sequence": 100,
    "init_xml" : [
    ],
    "data" : [
        'security/of_group_intranet_security.xml',
        'of_base_view.xml',
        'wizard/wizard_change_active_product.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
