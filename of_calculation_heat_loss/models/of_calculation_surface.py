# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFCalculationSurface(models.Model):
    _name = 'of.calculation.surface'
    _description = u"Tableau de correspondance entre parois et coefficient K"
    _order = "surface_type DESC, k_value DESC"

    name = fields.Char(string=u"Nom", compute='_compute_name')
    surface_type = fields.Selection(
        selection=[('wall', u"Murs"), ('roof', u"Toiture"), ('floor', u"Plancher bas")],
        string=u"Parois", required=True)
    description = fields.Char(string=u"Description")
    k_value = fields.Float(string=u"Valeur du K", required=True)

    @api.depends('description', 'k_value')
    def _compute_name(self):
        for rec in self:
            rec.name = "%s - %s K" % (rec.description or "", rec.k_value)
