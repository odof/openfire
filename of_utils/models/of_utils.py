# -*- coding: utf-8 -*-

from odoo import models, fields


class BigInteger(fields.Integer):
    column_type = ('int8', 'int8')


class OFMois(models.Model):
    _name = 'of.mois'
    _description = u"Mois de l'année"
    _order = 'id'

    name = fields.Char('Mois', size=16)
    abr = fields.Char(u'Abréviation', size=16)
    numero = fields.Integer(string=u"Numéro", readonly=True)

    _sql_constraints = [
        ('numero_uniq', 'unique(numero)', u'Deux mois ne peuvent pas avoir le même numéro')
    ]


class OFJours(models.Model):
    _name = 'of.jours'
    _description = "Jours de la semaine"
    _order = 'id'

    name = fields.Char('Jour', size=16)
    abr = fields.Char(u'Abréviation', size=16)
    numero = fields.Integer(string=u"Numéro", readonly=True)

    _sql_constraints = [
        ('numero_uniq', 'unique(numero)', u'Deux jours ne peuvent pas avoir le même numéro')
    ]
