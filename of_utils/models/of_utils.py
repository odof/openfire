# -*- coding: utf-8 -*-

import re
import unicodedata
from PIL import Image
from math import asin, sin, cos, sqrt, radians
from odoo import models, fields, _, tools
from odoo.tools.safe_eval import safe_eval

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


def get_selection_label(self, object, field_name, field_value):
    """Get a translation of the displayed string value from a selection field for a given model
    :param object: Model of the field selection
    :param field_name: Name of the field in the model
    :param field_value: Selection value of the field
    :return: The translated string value of the selection field if the translation exist (else the original value)
    """
    return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])


def arrondi_sup(val, mult):
    """
    Arrondi au multiple supérieur
    :param val: Valeur à arrondir
    :param mult: Multiplicateur
    :return: Valeur arrondie au multiple supérieur de Multiplicateur
    """
    if val % mult:
        val = mult * (int(val / mult) + 1)
    return val


def distance_points(lat1, lon1, lat2, lon2):
    u"""
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param: Coordonnées gps en degrés
    """
    lat1, lon1, lat2, lon2 = [radians(v) for v in (lat1, lon1, lat2, lon2)]
    return 2*asin(sqrt((sin((lat1-lat2)/2)) ** 2 + cos(lat1)*cos(lat2)*(sin((lon1-lon2)/2)) ** 2)) * 6366


def format_date(date_eval, lang, with_year=True):
    # Si la date est en string, la convertir en date puis lui appliquer le format. Sinon, lui appliquer le format
    if isinstance(date_eval, basestring):
        res = fields.Date.from_string(date_eval).strftime(lang.date_format)
    else:
        res = date_eval.strftime(lang.date_format)
    if not with_year:
        res = res[:-5]
    return res


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


def hours_to_strs(*args):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    # Si le premier argument est un string, c'est le mode
    if args and isinstance(args[0], basestring):
        mode = args[0]
        hours = args[1:]
    else:
        mode = 'default'
        hours = args
    if mode == 'time':
        return tuple("%02d:%02d" % (hour, round((hour % 1) * 60)) for hour in hours)
    return tuple("%dh%02d" % (hour, round((hour % 1) * 60)) if hour % 1 else "%dh" % hour for hour in hours)


def float_2_heures_minutes(flo):
    heures = flo // 1
    minutes = (flo - heures) * 60
    return heures, minutes


def heures_minutes_2_float(heures, minutes):
    return heures + minutes / 60.0


def compare_date(date1, date2, compare="==", isdatetime=False):
    if not date1 or not date2:
        return False
    date1 = fields.Datetime.from_string(date1)
    date2 = fields.Datetime.from_string(date2)
    return safe_eval("date1 " + compare + " date2",
                     {'date1': date1.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date1.strftime("%d/%m/%Y"),
                      'date2': date2.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date2.strftime("%d/%m/%Y")})


def sanitize_text(text, allowed=''):
    """
    Cette fonction nettoie un texte en remplaçant les caractères non-ascii.
    Les caractères seront remplacés par un équivalent si possible (e.g. lettres accentuées) ou supprimés sinon.
    Seuls les chiffres, lettres, et caractères de allowed seront conservés, les autres supprimés.
    :param text: Texte à nettoyer.
    :param allowed: Caractères spéciaux ASCII autorisés (ponctuation, espaces blancs, etc.).
    :return: texte nettoyé.
    """
    # Retrait de tous les caractères spéciaux.
    # Les caractères accentués sont remplacés par leur version sans accent.
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')
    allowed = re.escape(allowed)
    return re.sub('[^0-9A-Za-z%s]' % allowed, '', text)


def is_valid_url(of_url):
    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return of_url is not None and regex.search(of_url)


def intersect_couple(hour_couple1, hour_couple2):
    # on compare deux couples d'heures, si ce n'est pas un couple alors on ne compare pas
    if not len(hour_couple1) == 2 or not len(hour_couple2) == 2:
        return (0, 0)
    hour_debut = 0
    hour_fin = 0
    # si hour_debut du couple 2 est supérieur à celui du couple 1, alors hour_debut = hour_couple2[0]
    # sinon hour_debut = hour_couple1[0]
    hour_debut = max(hour_couple1[0], hour_couple2[0])
    # si hour_fin du couple 2 est inférieur à celui du couple 1, alors hour_fin = hour_couple2[1]
    # sinon hour_fin = hour_couple1[1]
    hour_fin = min(hour_couple1[1], hour_couple2[1])
    # si hour_min > hour_max, ce n'est pas un créneau que l'on peut utiliser
    if hour_debut > hour_fin:
        hour_debut, hour_fin = (0, 0)
    return (hour_debut, hour_fin)


def resize_image(image_data, width, height):
    # Decode the base64 image to bytes
    image_stream = StringIO.StringIO(image_data.decode('base64'))
    image_opened = Image.open(image_stream)
    if image_opened.size[0] > width or image_opened.size[1] > height:
        # inverser width et height permet de passer de paysage à portrait
        size = (width, height) if image_opened.size[0] > image_opened.size[1] else (height, width)
        resized_image = tools.image_resize_and_sharpen(
            image_opened, size, preserve_aspect_ratio=True
        )
        background_stream = StringIO.StringIO()
        resized_image.save(background_stream, image_opened.format)
        image_data = background_stream.getvalue().encode('base64')
    return image_data


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
