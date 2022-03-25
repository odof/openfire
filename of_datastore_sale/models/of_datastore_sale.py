# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFDatastoreSale(models.Model):
    _name = 'of.datastore.sale'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur de vente"
    _rec_name = 'db_name'
    _order = 'db_name'

    active = fields.Boolean(string=u"Actif", default=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Client",
        domain=[('customer', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)])

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.multi
    def button_dummy(self):
        return True
