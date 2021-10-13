# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import json
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from odoo.tools import config
from odoo.addons.of_geolocalize.models.of_geo import GEO_PRECISION
from odoo.addons.of_utils.models.of_utils import hours_to_strs, distance_points as voloiseau, arrondi_sup
import urllib
import requests

class OfPlanifCreneauProp(models.TransientModel):
    _inherit = 'of.planif.creneau.prop'

    parc_installe_product_name = fields.Char(
        string=u"Désignation", related="service_id.parc_installe_id.product_id.name", readonly=True)
