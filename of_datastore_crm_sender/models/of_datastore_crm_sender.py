# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFDatastoreCRM(models.Model):
    _name = 'of.datastore.crm.sender'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur CRM"
    _rec_name = 'db_name'
    _order = 'db_name'

    active = fields.Boolean(string=u"Actif", default=True)
    partner_id = fields.Many2one('res.partner', string=u"Membre réseau")
    datastore_id = fields.Char(string=u"Identifiant", required=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.multi
    def button_dummy(self):
        return True

    @api.model
    def create(self, values):
        if 'partner_id' in values:
            # On passe le partner en membre réseau
            if values['partner_id']:
                self.env['res.partner'].browse(values['partner_id']).of_network_member = True

        return super(OFDatastoreCRM, self).create(values)

    @api.multi
    def write(self, values):
        if 'partner_id' in values:
            # On passe l'ancien membre réseau à False
            if self.partner_id:
                self.partner_id.of_network_member = False

            # On passe le nouveau à True
            if values['partner_id']:
                self.env['res.partner'].browse(values['partner_id']).of_network_member = True

        return super(OFDatastoreCRM, self).write(values)
