# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_financing_organism = fields.Many2one(comodel_name='res.partner', string=u"Organisme de financement")
    of_financing_file_number = fields.Char(string=u"Numéro de dossier du financement")
    of_financing_state = fields.Selection(
        selection=[('new', u"Nouveau"),
                   ('in_progress', u"En cours"),
                   ('accepted', u"Accepté"),
                   ('refused', u"Refusé")], string=u"État du financement")
    of_financing_decision_date = fields.Date(string=u"Date de décision du financement")
    of_financing_amount = fields.Float(string=u"Montant du financement")
    of_financing_monthly_payment_number = fields.Integer(string=u"Nombre de mensualités du financement")
    of_financing_rate = fields.Float(string=u"Taux de financement (%)")
    of_financing_printing = fields.Boolean(string=u"Impression de financement")
    of_financing_notes = fields.Text(string=u"Mentions du financement")
