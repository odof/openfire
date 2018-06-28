# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date
import pytz
import math
from math import cos
from odoo.addons.of_planning_tournee.models.of_planning_tournee import distance_points
from odoo.exceptions import UserError


NEW_RES_MODES = [
    ('distance_top_view', u"Distance à vol d'oiseau"),
    ('distance_by_road', u"Distance à parcourir"),
    ('time_by_road', u'Temps de trajet'),
]

class OfTourneeRdv(models.TransientModel):
    _inherit = 'of.tournee.rdv'

    mode2 = fields.Selection(NEW_RES_MODES, string="Mode de recherche", required=True, default="distance_top_view")
    date_recherche_debut = fields.Date(string='Date debut', required=True, default=lambda *a: (date.today()).strftime('%Y-%m-%d'))
    date_recherche_fin = fields.Date(string='Date fin', required=True, default=lambda *a: (date.today() + timedelta(days=15)).strftime('%Y-%m-%d'))
    distance_in_top_view = fields.Float(string=u'Distance aérienne', digits=(8, 2), required=True, default=10, help=u'Éloignement maximum en ligne droite (km)')
    distance_in_road = fields.Float(string=u'Distance par route', digits=(8, 2), required=True, default=10, help=u'Éloignement maximum par route (km)')
    time_in_road = fields.Float(string=u"Temps par route", required=True, help=u"Temps maximum par route")






