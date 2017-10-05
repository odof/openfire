# -*- encoding: utf-8 -*-

from odoo import models, fields, api


class OFMois(models.Model):
    _name = 'of.mois'
    _description = u"Mois de l'année"
    _order = 'id'

    name = fields.Char('Mois', size=16)
    abr = fields.Char(u'Abréviation', size=16)

class OFJours(models.Model):
    _name = 'of.jours'
    _description = "Jours de la semaine"
    _order = 'id'

    name = fields.Char('Jour', size=16)
    abr = fields.Char(u'Abréviation', size=16)

class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    stock_warning_setting = fields.Boolean(string="Avertissements de stock", required=True, default=False,
            help="Afficher les messages d'avertissement de stock?")

    @api.multi
    def set_utils_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'stock_warning_setting', self.stock_warning_setting)
