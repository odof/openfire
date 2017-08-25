# -*- coding: utf-8 -*-

from odoo import api, models, fields

class OFUsers(models.Model):
    _inherit = 'res.users'

    of_color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0", oldname="color_bg")

class OFPartners(models.Model):
    _inherit = 'res.partner'

    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_colors", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_colors", oldname="color_bg")

    @api.depends("user_ids")
    def _compute_colors(self):
        for partner in self:
            if partner.user_ids:
                partner.of_color_ft = partner.user_ids[0].of_color_ft
                partner.of_color_bg = partner.user_ids[0].of_color_bg
            else:
                partner.of_color_ft = "#0D0D0D"
                partner.of_color_bg = "#F0F0F0"

class OFMeeting(models.Model):
    _inherit = "calendar.event"

    color_partner_id = fields.Many2one("res.partner", "Partner whose color we will take", compute='_compute_color_partner', store=False)
    of_color_ft = fields.Char(string="Couleur de texte", help="Couleur de texte de l'utilisateur", compute="_compute_of_color")
    of_color_bg = fields.Char(string="Couleur de fond", help="Couleur de fond de l'utilisateur", compute="_compute_of_color")

    @api.multi
    @api.depends('color_partner_id')
    def _compute_of_color(self):
        for meeting in self:
            meeting.of_color_bg = meeting.color_partner_id.of_color_bg
            meeting.of_color_ft = meeting.color_partner_id.of_color_ft

    @api.multi
    @api.depends('user_id')
    def _compute_color_partner(self):
        for meeting in self:
            if meeting.user_id.partner_id in meeting.partner_ids:
                meeting.color_partner_id = meeting.user_id.partner_id
            else:
                meeting.color_partner_id = (filter(lambda partner:partner.user_ids, meeting.partner_ids) or [False])[0]
