# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_supplier_edi = fields.Boolean(string=u"Envoi EDI pour ce fournisseur ?")
