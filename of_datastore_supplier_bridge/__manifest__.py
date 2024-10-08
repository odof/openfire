# -*- coding: utf-8 -*-

{
    'name': "OpenFire / Base centrale intermédiaire des articles",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour bases de centralisation intermédiaires des tarifs.
=======================================================================

Module destiné aux bases qui sont à la fois fournisseur et récupèrent leurs tarifs d'une autre base centrale.

- Rend disponible le bouton "Importer tous les articles" depuis la marque aux utilisateurs non admin.
""",
    'depends': ['of_datastore_product', 'of_datastore_supplier'],
    'data': [
        'views/of_datastore_supplier_bridge_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
