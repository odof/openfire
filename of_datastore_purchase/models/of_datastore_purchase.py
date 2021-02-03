# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFDatastorePurchase(models.Model):
    _name = 'of.datastore.purchase'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur d'achat"
    _rec_name = 'db_name'
    _order = 'db_name'

    active = fields.Boolean(string=u"Actif", default=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Fournisseur",
        domain=[('supplier', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)])
    datastore_id = fields.Char(string=u"Identifiant chez le fournisseur", required=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.multi
    def button_dummy(self):
        return True

