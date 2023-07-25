# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OFDocumentType(models.Model):
    _name = 'of.document.type'
    _description = u"Type de document"

    name = fields.Char(string=u"Nom", required=True)
