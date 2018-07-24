# -*- coding: utf-8 -*-

from odoo import api, models, fields

class OfMailTemplate(models.Model):
    _inherit = "of.mail.template"

    type = fields.Selection(selection_add=[('contrat', 'Contrat')])

class OFService(models.Model):
    _inherit = "of.service"

    contrat = fields.Many2one('of.mail.template', string='Contrat', domain="[('type', '=', 'contrat')]")
    date_contrat = fields.Date(string="Date du contrat")
