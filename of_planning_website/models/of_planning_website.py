# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random

from odoo import api, models, fields, tools, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_geo_comment = fields.Text(
        string=u"Commentaire du client", help=u"Commentaire du client rempli lors de la prise de RDV en ligne")


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    website_create = fields.Boolean(string=u"Créé par le portail web")


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    website_create = fields.Boolean(string=u"Créé par le portail web")
