# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_invoice_policy = fields.Selection(selection_add=[('intervention', u'Quantités planifiées')])
