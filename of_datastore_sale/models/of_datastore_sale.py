# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFDatastoreSale(models.Model):
    _name = 'of.datastore.sale'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur de vente"
    _rec_name = 'db_name'
    _order = 'db_name'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr

        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % ('of_datastore_sale_partner_rel',))
        exists = cr.fetchall()
        res = super(OFDatastoreSale, self)._auto_init()
        if not exists:
            datastores = self.env['of.datastore.sale'].search([])
            for datastore in datastores:
                datastore.write({'partner_ids': [(4, datastore.partner_id.id)]})
        return res

    active = fields.Boolean(string=u"Actif", default=True)
    partner_ids = fields.Many2many(
        comodel_name='res.partner', relation='of_datastore_sale_partner_rel', string=u"Clients",
        domain=[('customer', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)])
    partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Client",
        domain=[('customer', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)])

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.multi
    def button_dummy(self):
        return True
