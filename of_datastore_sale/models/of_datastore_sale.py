# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class OFDatastoreSale(models.Model):
    _name = 'of.datastore.sale'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur de vente"
    _rec_name = 'db_name'
    _order = 'db_name'

    active = fields.Boolean(string=u"Actif", default=True)
    # A supprimer à la prochaine MAJ
    partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Client",
        domain=[('customer', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)])
    partner_ids = fields.Many2many(
        comodel_name='res.partner', relation='datastore_partner_rel',
        column1='datastore_id', column2='partner_id', string=u"Clients", copy=False,
        domain=[('customer', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)])

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.multi
    def button_dummy(self):
        return True
