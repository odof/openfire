# -*- coding: utf-8 -*-
{
    'name': 'OpenFire / Gestion des documents',
    'author': 'OpenFire',
    'version': '1.0',
    'category': 'Gestion Documents',
    'description': u"""Module OpenFire pour la gestion de documents.
    - Nécessite l'installation de pdfminer et pypdftk sur le serveur
""",
    'depends': ['crm', 'sale'],
    "update_xml" : [
        'views/mail_template_view.xml',
        'wizard/compose_mail_view.xml',
        'security/ir.model.access.csv',
    ],
}
