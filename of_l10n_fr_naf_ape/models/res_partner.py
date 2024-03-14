# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    of_ape_id = fields.Many2one(
        comodel_name='of.naf', string=u"Code APE",
        help=u"Si le partenaire est une société française, saisissez son activité principale dans ce champ. "
        "L'APE est choisi dans la nomenclature NAF.")
