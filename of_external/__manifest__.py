# -*- coding: utf-8 -*-

{
    'name': 'OpenFire en-tête et pied de page personnalisés',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Rendu en-tête pied de page des rapports pdf',
    'description': """
Module OpenFire pour les en-têtes et les pieds de page des rapports pdf
=======================================================================

Module redéfinissant l'entête et pied de page de rapport externe

Ajoute un onglet de configuration de l'en-tête et du pied de page dans la fiche société

Utilisation des variables Mako pour intégrer des champs aux lignes d'en-tête et de pied de page
    """,
    'website': 'openfire.fr',
    'depends': [
        'report',
        'of_base',
        'mail',
        'stock',
    ],
    'data': [
        'wizard/of_external_wizard_views.xml',
        'report/of_external_report_templates.xml',
        'views/of_company_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
