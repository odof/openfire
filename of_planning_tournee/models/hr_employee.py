# -*- coding: utf-8 -*-

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    of_tournee_ids = fields.One2many('of.planning.tournee', 'employee_id', string=u"Tournées")
