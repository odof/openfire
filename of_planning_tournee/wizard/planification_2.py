# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta
import math
from math import cos
import pytz
from pytz import timezone
from odoo.addons.of_planning_tournee.models.of_planning_tournee import distance_points
from odoo.addons.of_planning_tournee.wizard.rdv import hours_to_strs
from odoo.exceptions import UserError
from __builtin__ import True


