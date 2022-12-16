# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
import unicodedata
from math import asin, sin, cos, sqrt, radians
from odoo import fields, _
from odoo.tools.safe_eval import safe_eval


def get_selection_label(self, object, field_name, field_value):
    """Get a translation of the displayed string value from a selection field for a given model
    :param object: Model of the field selection
    :param field_name: Name of the field in the model
    :param field_value: Selection value of the field
    :return: The translated string value of the selection field if the translation exist (else the original value)
    """
    return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])


def ceil_to_multiple(val, mult):
    """
    Arrondi au multiple supérieur
    :param val: Valeur à arrondir
    :param mult: Multiplicateur
    :return: Valeur arrondie au multiple supérieur de Multiplicateur
    """
    if val % mult:
        val = mult * (int(val / mult) + 1)
    return val


def distance_between_points(lat1, lon1, lat2, lon2):
    """
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param: Coordonnées gps en degrés
    """
    lat1, lon1, lat2, lon2 = [radians(v) for v in (lat1, lon1, lat2, lon2)]
    return 2 * asin(sqrt((sin((lat1 - lat2) / 2)) ** 2 + cos(lat1) * cos(lat2) * (sin((lon1-lon2) / 2)) ** 2)) * 6366


def format_date(date_eval, lang, with_year=True):
    # Si la date est en string, la convertir en date puis lui appliquer le format. Sinon, lui appliquer le format
    if isinstance(date_eval, str):
        res = fields.Date.from_string(date_eval).strftime(lang.date_format)
    else:
        res = date_eval.strftime(lang.date_format)
    if not with_year:
        res = res[:-5]
    return res


def intervals_overlap(min_1, max_1, min_2, max_2, strict=True):
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
    if args and isinstance(args[0], str):
        mode = args[0]
        hours = args[1:]
    else:
        mode = 'default'
        hours = args
    if mode == 'time':
        return tuple("%02d:%02d" % (hour, round((hour % 1) * 60)) for hour in hours)
    return tuple("%dh%02d" % (hour, round((hour % 1) * 60)) if hour % 1 else "%dh" % hour for hour in hours)


def float_2_hours_minutes(flo):
    heures = flo // 1
    minutes = (flo - heures) * 60
    return heures, minutes


def hours_minutes_2_float(heures, minutes):
    return heures + minutes / 60.0


def compare_date(date1, date2, compare="==", isdatetime=False):
    if not date1 or not date2:
        return False
    date1 = fields.Datetime.from_string(date1)
    date2 = fields.Datetime.from_string(date2)
    return safe_eval(
        f"date1 {compare} date2",
        {
            'date1': date1.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date1.strftime("%d/%m/%Y"),
            'date2': date2.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date2.strftime("%d/%m/%Y")
        }
    )


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
    return re.sub(f'[^0-9A-Za-z{allowed}]', '', text)


def is_valid_url(of_url):
    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return of_url is not None and regex.search(of_url)


# Deprecated, kept for backward compatibility.
arrondi_sup = ceil_to_multiple
distance_points = distance_between_points
se_chevauchent = intervals_overlap
float_2_heures_minutes = float_2_hours_minutes
heures_minutes_2_float = hours_minutes_2_float
