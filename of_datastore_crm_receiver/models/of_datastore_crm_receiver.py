# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFDatastoreCRMChild(models.Model):
    _name = 'of.datastore.crm.receiver'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur CRM"
    _rec_name = 'db_name'
    _order = 'db_name'

    active = fields.Boolean(string=u"Actif", default=True)
    datastore_id = fields.Char(string=u"Identifiant", required=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.multi
    def button_dummy(self):
        return True
