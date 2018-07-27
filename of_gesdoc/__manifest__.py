# -*- coding: utf-8 -*-
{
    'name': 'OpenFire Gestion des documents',
    'author': 'OpenFire',
    'version': '10.0.1.0.0',
    'category': 'Gestion Documents',
    'description': u"""Module OpenFire pour la gestion de documents.
---------------------------------------------

Permet la création de documents pdf personnalisés depuis les partenaires, bons de commande et factures.
Permet le remplissage automatique d'un document pdf éditable.

Ajoute une fonctionnalité de mise à jour des données par l'import d'un document pdf
Fonctionnalité pour l'instant disponible uniquement pour les SAV, via le module of_project_issue

- Nécessite l'installation de pdfminer et pypdftk sur le serveur
""",
    'depends': ['crm', 'sale'],
    'external_dependancies': {
        'python': ['pdfminer', 'pypdftk'],
    },
    'data' : [
        'views/mail_template_view.xml',
        'wizard/compose_mail_view.xml',
        'wizard/import_mail_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
