# -*- coding: utf-8 -*-

from openerp import models, fields

class project_issue(models.Model):
    _inherit = "res.partner"

    of_date_naissance = fields.Date(u'Date de naissance')
    of_date_naissance_char = fields.Char(u'Date anniversaire (MM-JJ)', compute='return')
