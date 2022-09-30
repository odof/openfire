# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class OFDatastoreCRM(models.Model):
    _name = 'of.datastore.crm.sender'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur CRM"
    _rec_name = 'db_name'
    _order = 'db_name'

    active = fields.Boolean(string=u"Actif", default=True)
    is_multicompany = fields.Boolean(string=u"Multi-société", compute='_compute_is_multicompany')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Membre réseau")
    child_ids = fields.One2many(
        comodel_name='of.datastore.crm.network.member', inverse_name='parent_id', string=u"Membres réseau")
    datastore_id = fields.Char(string=u"Identifiant", required=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.multi
    def button_dummy(self):
        return True

    @api.multi
    def button_load_companies(self):
        for datastore_crm in self:
            client = datastore_crm.of_datastore_connect()
            if isinstance(client, basestring):
                raise UserError(u"Échec de la connexion au connecteur CRM !")

            ds_company_obj = datastore_crm.of_datastore_get_model(client, 'res.company')

            # On récupère les sociétés sur la base fille
            company_ids = datastore_crm.of_datastore_search_read(ds_company_obj,  [], ['name'])
            datastore_network_member_obj = self.env['of.datastore.crm.network.member']
            for company in company_ids:
                if company['name'] not in datastore_crm.child_ids.mapped('company'):
                    datastore_network_member_obj.create({
                        'parent_id': datastore_crm.id,
                        'company': company['name'],
                        'company_id': company['id'],
                    })
        return True

    @api.depends()
    def _compute_is_multicompany(self):
        for datastore in self:
            client = datastore.of_datastore_connect()
            if isinstance(client, basestring):
                datastore.is_multicompany = False
            else:
                ds_company_obj = datastore.of_datastore_get_model(client, 'res.company')

                # On récupère les sociétés sur la base fille
                company_ids = datastore.of_datastore_search(ds_company_obj, [])
                datastore.is_multicompany = len(company_ids) > 1

    @api.model
    def create(self, values):
        if values.get('partner_id'):
            # On passe le partner en membre réseau
            self.env['res.partner'].browse(values['partner_id']).of_network_member = True
        return super(OFDatastoreCRM, self).create(values)

    @api.multi
    def write(self, values):
        if 'partner_id' in values:
            # On passe le nouveau à True
            if values['partner_id']:
                self.env['res.partner'].browse(values['partner_id']).of_network_member = True
            for datastore in self:
                # On passe l'ancien membre réseau à False
                if not datastore.is_multicompany and datastore.partner_id:
                    datastore.partner_id.of_network_member = False
        return super(OFDatastoreCRM, self).write(values)


class OFDatastoreCRMNetworkMember(models.Model):
    _name = 'of.datastore.crm.network.member'
    _description = u"Membres réseau"

    parent_id = fields.Many2one(
        comodel_name='of.datastore.crm.sender', string=u"Connecteur CRM", ondelete='cascade', required=True)
    company = fields.Char(string=u"Société", ondelete='cascade', required=True)
    company_id = fields.Integer(string=u"ID de la Société sur la base distante", required=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Membre réseau")

    @api.constrains('partner_id')
    @api.multi
    def _check_partner_id(self):
        if any(len(line.parent_id.child_ids.filtered(
                lambda l: l.partner_id and l.partner_id == line.partner_id)) > 1 for line in self):
            raise ValidationError(
                u'Vous ne pouvez pas renseigner deux fois le même membre réseau pour deux sociétés différentes.')

    @api.model
    def create(self, values):
        if values.get('partner_id'):
            # On passe le partner en membre réseau
            self.env['res.partner'].browse(values['partner_id']).of_network_member = True
        return super(OFDatastoreCRMNetworkMember, self).create(values)

    @api.multi
    def write(self, values):
        if 'partner_id' in values:
            # On passe le nouveau à True
            if values['partner_id']:
                self.env['res.partner'].browse(values['partner_id']).of_network_member = True
            for child in self:
                # On passe l'ancien membre réseau à False
                if child.partner_id:
                    child.partner_id.of_network_member = False

        return super(OFDatastoreCRMNetworkMember, self).write(values)
