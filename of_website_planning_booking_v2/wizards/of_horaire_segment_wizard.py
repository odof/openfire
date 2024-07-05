# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class OFHoraireSegmentWizard(models.TransientModel):
    _inherit = 'of.horaire.segment.wizard'

    type = fields.Selection(selection_add=[('website', u"Web")])
