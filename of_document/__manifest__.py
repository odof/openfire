# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Gestion électronique des documents",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'website': u"http://www.openfire.fr",
    'category': u"Gestion électronique des documents",
    'description': u"""
Module OpenFire pour la gestion électronique des documents
==========================================================

Module basé sur les modules Muk DMS avec les ajouts/modifications suivantes :
-----------------------------------------------------------------------------

- Modification du système de stockage pour utiliser le filestore standard Odoo
- Centralisation des pièces jointes liées aux objets suivants dans un répertoire unique par partenaire :
    - Partenaires
    - Commandes de vente
    - Commandes d'achat
    - Factures
    - Bons de livraison
    - Bons de réception
    - Opportunités
    - SAV
    - Interventions
    - RDVS d'intervention
- Gestion des droits utilisateurs à l'image des droits des pièces jointes (i.e. même droits que sur l'objet lié)
- Ajout de catégories et d'étaiquettes sur les fichiers GED
- Ajout du chatter sur les fichiers GED
- Mise en place de smarts boutons pour accéder aux fichiers GED depuis un partenaire, et aux objets liés depuis un fichier GED
- Modification des menus
- Corrections diverses sur la vue arborescence JS (ordre et recherche)
""",
    'depends': [
        'muk_dms',
        'muk_web_preview_attachment',
        'muk_web_preview_image',
        'sale',
        'purchase',
        'account',
        'stock',
        'crm',
        'project',
        'of_service',
        'of_base',
    ],
    'data': [
        'data/of_document_data.xml',
        'security/of_document_security.xml',
        'security/ir.model.access.csv',
        'views/dms_views.xml',
        'views/partner_views.xml',
        'views/sale_views.xml',
        'views/of_document_templates.xml',
        'wizards/mail_compose.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
