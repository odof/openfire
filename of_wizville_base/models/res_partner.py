# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_wizville_satisfaction = fields.Char(string=u"Satisfaction globale")
    of_nps_pose_score = fields.Char(string=u"Score NPS")
    of_nps_date_envoi = fields.Char(string=u"Date d'envoi du NPS")
    of_nps_date_reponse = fields.Char(string=u"Date de réponse du NPS")
