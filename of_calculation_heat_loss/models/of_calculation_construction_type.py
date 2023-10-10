# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFCalculationConstructionType(models.Model):
    _name = 'of.calculation.construction.type'
    _description = u"Type de bâtiment"
    _order = 'sequence'

    name = fields.Char(string=u"Nom", required=True)
    sequence = fields.Integer(string=u"Séquence")
    intermittency_coefficient = fields.Float(string=u"Coefficient d'intermittence", required=True)
