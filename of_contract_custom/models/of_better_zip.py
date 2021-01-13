# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfSecteur(models.Model):
    _inherit = 'of.secteur'

    partner_id = fields.Many2one(comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]")
