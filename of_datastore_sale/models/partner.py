# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_datastore_id = fields.Char(string=u"Identifiant pour le connecteur de vente", copy=False)
