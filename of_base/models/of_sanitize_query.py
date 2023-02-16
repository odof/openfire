# -*- coding: utf-8 -*-

from odoo import models, fields


class OFSanitizeQuery(models.Model):
    _name = 'of.sanitize.query'

    query_if = fields.Char()
    query = fields.Char(required=True)
