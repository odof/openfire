# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Archives OpenFlam",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Outil d'archives externes dans OpenFlam.

Permet d'uploader des documents externes afin de les archiver dans OpenFlam.
Chaque archive peut être typée (par défaut "Facture", "Avoir", "Devis", "Commande") et associée à l'objet Partenaire. Il est également possible d'y associer des données partenaires statiques.

Les documents sont importés en masse via l'outil d'import, il suffit de préciser le dossier local où se trouve les documents et le format des documents à importer.

Un widget pour visualiser les documents au format PDF a été mis en place sur l'objet Archive.
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_base',
    ],
    'data': [
        'data/archive_type.xml',
        'security/ir.model.access.csv',
        'views/of_archive_views.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
        'views/templates.xml',
    ],
    'qweb': ['static/src/xml/of_archive.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
