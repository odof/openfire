# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
import unicodedata
from math import asin, cos, radians, sin, sqrt

from odoo import _, fields
from odoo.tools.safe_eval import safe_eval


def get_selection_label(self, res_model, field_name, field_value):
    """Get a translation of the displayed string value from a selection field for a given model

    Args:
        self: Environment
        res_model: Model of the field selection
        field_name: Name of the field in the model
        field_value: Selection value of the field

    Returns:
        The translated string value of the selection field if the translation exist (else the original value)
    """
    return _(dict(self.env[res_model].fields_get(allfields=[field_name])[field_name]["selection"])[field_value])


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
    return 2 * asin(sqrt((sin((lat1 - lat2) / 2)) ** 2 + cos(lat1) * cos(lat2) * (sin((lon1 - lon2) / 2)) ** 2)) * 6366


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
    """Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'"""
    # Si le premier argument est un string, c'est le mode
    if args and isinstance(args[0], str):
        mode = args[0]
        hours = args[1:]
    else:
        mode = "default"
        hours = args
    if mode == "time":
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
            "date1": date1.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date1.strftime("%d/%m/%Y"),
            "date2": date2.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date2.strftime("%d/%m/%Y"),
        },
    )


def sanitize_text(text, allowed=""):
    """This function cleans a text by replacing non-ascii characters.

    Characters will be replaced by an equivalent if possible (e.g. accented letters) or removed otherwise.
    Only digits, letters, and characters from allowed will be kept, others removed.

    Args:
        text: Text to clean.
        allowed: Allowed ASCII special characters (punctuation, whitespace, etc.).

    Returns:
        Cleaned text.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    allowed = re.escape(allowed)
    return re.sub(f"[^0-9A-Za-z{allowed}]", "", text)


def is_valid_url(of_url):
    regex = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return of_url is not None and regex.search(of_url)


def intersection_hours_couple(hour_couple1, hour_couple2):
    """Check if two hours couples intersect
    :param hour_couple1: First hours couple
    :type hour_couple1: tuple
    :param hour_couple2: Second hours couple
    :type hour_couple2: tuple
    :return: Return a tuple with the intersection of the two hours couples
    """
    # on compare deux couples d'heures, si ce n'est pas un couple alors on ne compare pas
    if len(hour_couple1) != 2 or len(hour_couple2) != 2:
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


# Deprecated, kept for backward compatibility.
arrondi_sup = ceil_to_multiple
distance_points = distance_between_points
se_chevauchent = intervals_overlap
float_2_heures_minutes = float_2_hours_minutes
heures_minutes_2_float = hours_minutes_2_float
intersect_couple = intersection_hours_couple
