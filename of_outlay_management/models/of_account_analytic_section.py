# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFAccountAnalyticSection(models.Model):
    _name = 'of.account.analytic.section'
    _description = u"Section analytique"

    name = fields.Char(string=u"Libellé")
