# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    of_crm_stage_id = fields.Selection(selection=[
        ('1', u"1"),
        ('2', u"2"),
        ('3', u"3"),
        ('4', u"4"),
        ('5', u"5"),
        ('6', u"6"),
        ('7', u"7"),
        ('8', u"8"),
        ('9', u"9"),
        ('10', u"10"),
        ('11', u"11"),
        ('12', u"12"),
        ('13', u"13"),
        ('14', u"14"),
        ('15', u"15"),
        ('16', u"16"),
        ('17', u"17"),
        ('18', u"18"),
        ('19', u"19"),
        ('20', u"20"),
    ], string=u"Identifiant de l'étape de l'opportunité source", copy=False)

    _sql_constraints = [
        ('of_crm_stage_id_uniq', 'unique (of_crm_stage_id)', u"Il existe déjà une étape kanban avec cet identifiant")
    ]
