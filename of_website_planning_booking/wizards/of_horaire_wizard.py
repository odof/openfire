# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OFHoraireSegmentWizard(models.TransientModel):
    _inherit = 'of.horaire.segment.wizard'

    type = fields.Selection(selection_add=[('website', u"Web")])
