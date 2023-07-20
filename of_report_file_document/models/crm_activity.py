# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class CRMActivity(models.Model):
    _inherit = 'crm.activity'

    of_document_type_id = fields.Many2one(comodel_name='of.document.type', string=u"Type de document")
