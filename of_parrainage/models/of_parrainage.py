# -*- coding: utf-8 -*-Je

from odoo import models, fields, api, SUPERUSER_ID


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_referred_reward_id = fields.Many2one('of.referred.reward', string=u"Récompense")
    of_referred_note = fields.Text(string="Notes")
    of_referred_reward_state = fields.Boolean(string="Clos")
    of_referred_reward_date = fields.Date(string=u"Date de récompense")

    @api.onchange('of_referred_reward_id')
    def onchange_referred_reward(self):
        if self.of_referred_reward_id and not self.of_referred_reward_date:
            self.of_referred_reward_date = fields.Date.today()



class OfReferredReward(models.Model):
    _name = 'of.referred.reward'
    _order = 'sequence'

    sequence = fields.Integer(string=u"Séquence", default=10)
    name = fields.Char(string=u"Nom de la récompense")
