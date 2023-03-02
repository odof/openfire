# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _


class OFHoraireSegment(models.Model):
    _inherit = 'of.horaire.segment'
    _order = 'employee_id, tache_id, date_deb, permanent DESC'

    employee_id = fields.Many2one(required=False)
    tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche", ondelete='cascade')

