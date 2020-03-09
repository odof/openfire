# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    type_conduit = fields.Char(string='Type de conduit')
    type_air = fields.Char(string=u"Type d'arrivée d'air")
