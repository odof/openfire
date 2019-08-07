# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Stage(models.Model):
    _inherit = "note.stage"

    active = fields.Boolean("Active", default=True)

class Tag(models.Model):
    _inherit = "note.tag"

    active = fields.Boolean("Active", default=True)

class Note(models.Model):
    _inherit = 'note.note'

    of_user_ids = fields.Many2many('res.users', 'note_users_rel', 'note_id', 'user_id', string='Utilisateurs concernés')
    of_partner_id = fields.Many2one('res.partner', string='Client', ondelete='cascade')
