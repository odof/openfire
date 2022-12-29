# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class OFHrTimesheetCateg(models.Model):
    _inherit = "of.hr.timesheet.categ"

    timesheet_type = fields.Selection(
        selection=[
            ('spec', u"Spécifications"),
            ('dev', u"Développement"),
            ('validation', u"Validation"),
            ('other', u"Autre"),
        ], string=u"Type des feuilles de temps")
