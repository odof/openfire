# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_description = fields.Html(
        string="Description société site web",
        help=u"Ce descriptif concerne les sociétés autres que la société principale et sera ajouté "
             u"à la suite des informations de la société principale sur le footer du site web.")
