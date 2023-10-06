# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFCalculationG(models.Model):
    _name = 'of.calculation.g'
    _description = u"Tableau de correspondance entre valeurs K et coefficient G"
    _order = "volume_type ASC, g_value DESC"

    name = fields.Char(string=u"Nom", compute='_compute_name')
    volume_type = fields.Selection(
        selection=[
            ('IP1', u"IP1 - Volume < 270 m³, 1 niveau"),
            ('IP2', u"IP2 - Volume < 270 m³, 2 niveaux"),
            ('IG1', u"IG1 - Volume >= 270 m³, 1 niveau"),
            ('IG2/3', u"IG2/IG3 - Volume >= 270 m³, 2/3 niveaux"),
        ], string=u"Type de coefficient", required=True)
    k_wall = fields.Float(string=u"K mur", required=True)
    k_roof = fields.Float(string=u"K toiture", required=True)
    k_floor = fields.Float(string=u"K plancher bas", required=True)
    g_value = fields.Float(string=u"Valeur du G", required=True)

    @api.depends('volume_type', 'g_value')
    def _compute_name(self):
        for rec in self:
            rec.name = "%s - %s G" % (rec.volume_type, rec.g_value)
