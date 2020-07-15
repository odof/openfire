# -*- coding: utf-8 -*-

from odoo import models, fields
from math import asin, sin, cos, sqrt, radians

def voloiseau(lat1, lng1, lat2, lng2):
    u"""
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param *: Coordonnées gps en degrés
    """
    lat1, lng1, lat2, lng2 = [radians(v) for v in (lat1, lng1, lat2, lng2)]
    return 2 * asin(sqrt((sin((lat1 - lat2) / 2)) ** 2 + cos(lat1) * cos(lat2) * (sin((lng1 - lng2) / 2)) ** 2)) * 6366

def format_date(date, lang):
    return fields.Date.from_string(date).strftime(lang.date_format)

def se_chevauchent(min_1, max_1, min_2, max_2, strict=True):
    """
    Teste si les intervalles passés en paramètre se chevauchent.
    Fonctionne pour tous types de variables acceptant les opérateurs d'inégalité ( '<' '<=' '>=' '>' )
    :param strict: Si vrai, les intervalles doivent se chevaucher strictement (pas seulement se toucher)
    :return: True si les intervalles se chevauchent, False sinon.
    """
    if strict:
        return min_1 < max_2 and min_2 < max_1
    return min_1 <= max_2 and min_2 <= max_1

def float_2_heures_minutes(flo):
    heures = flo // 1
    minutes = (flo - heures) * 60
    return heures, minutes

def heures_minutes_2_float(heures, minutes):
    return heures + minutes / 60


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
