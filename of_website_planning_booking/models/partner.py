# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_geo_comment = fields.Text(
        string=u"Commentaire du client", help=u"Commentaire du client rempli lors de la prise de RDV en ligne")
