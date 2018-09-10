# -*- coding: utf-8 -*-
{
    'name' : "OpenFire / Migration",
    'version' : "0.9",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "Migration",
    'description': """
Module de migration OpenFire.
=============================

Module de migration depuis la version 6.1 vers la version 9.0.
A installer sur une base 9.0, avec ajout des tables 6.1 suffixées par "_61" (e.g. account_account_61).
Le processus de migration se lance par XML/RPC par l'appel de la fonction of.migration.process()
""",
    'depends' : [
        'account',
    ],
    'demo_xml' : [ ],
    'data': [
    ],
    'installable': False,
}
