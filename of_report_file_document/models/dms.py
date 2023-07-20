# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.addons.muk_dms.models import dms_base


class File(dms_base.DMSModel):
    _inherit = 'muk_dms.file'

    of_document_type_id = fields.Many2one(comodel_name='of.document.type', string=u"Type de document")
