# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from of_datastore_product import DATASTORE_IND


class OfDatastoreSupplier(models.Model):
    _name = 'of.datastore.supplier'
    _inherit = 'of.datastore.connector'
    _description = 'Centralized products connector'
    _rec_name = 'db_name'
    _order = "db_name"

    brand_ids = fields.One2many('of.product.brand', 'datastore_supplier_id', string='Allowed brands')
    datastore_brand_ids = fields.One2many(
        'of.datastore.supplier.brand', compute='_compute_datastore_brand_ids', inverse=lambda *args: True,
        string='Supplier brands')
    # many2many_tags ne fonctionne pas pour les champs one2Many
    display_brand_ids = fields.Many2many(
        'of.product.brand', compute='_compute_display_brand_ids', string='Allowed brands')
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', 'There is already a connection to this database')
    ]

    @api.depends()
    def _compute_datastore_brand_ids(self):
        supplier_brand_obj = self.env['of.datastore.supplier.brand']
        for supplier in self:
            datastore_brands = False
            client = supplier.of_datastore_connect()
            if not isinstance(client, basestring):
                ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
                ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
                if ds_brand_ids:
                    id_add = DATASTORE_IND * supplier.id
                    ds_brand_ids = [brand_id + id_add for brand_id in ds_brand_ids]
                    datastore_brands = supplier_brand_obj.browse(ds_brand_ids)
            supplier.datastore_brand_ids = datastore_brands

    @api.depends()
    def _compute_display_brand_ids(self):
        for supplier in self:
            supplier.display_brand_ids = supplier.brand_ids

    @api.onchange('server_address')
    def onchange_server_address(self):
        if self.server_address and not self.server_address.startswith('http'):
            return {'value': {'server_address': 'https://' + self.server_address}}
        return False

    @api.onchange('db_name')
    def onchange_db_name(self):
        if self.db_name:
            return {'value': {'server_address': 'https://' + self.db_name + '.openfire.fr'}}
        return False

    @api.multi
    def button_dummy(self):
        return True

    @api.multi
    def button_import_brands(self):
        self.ensure_one()
        wizard_obj = self.env['of.datastore.import.brand']
        client = self.of_datastore_connect()
        if isinstance(client, basestring):
            raise UserError(u'Échec de la connexion à la base centrale')
        ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
        ds_brand_ids = self.of_datastore_search(ds_brand_obj, [])
        ds_brand_data = self.of_datastore_read(ds_brand_obj, ds_brand_ids, ['name', 'code', 'logo', 'note_maj'])
        brand_names = self.env['of.product.brand'].search([]).mapped('name')

        wizard = wizard_obj.create({
            'datastore_supplier_id': self.id,
            'line_ids': [(0, 0, {
                'datastore_brand_id': ds_brand['id'],
                'name': ds_brand['name'],
                'code': ds_brand['code'],
                'logo': ds_brand['logo'],
                'note_maj': ds_brand['note_maj'],
                'state': 'done' if ds_brand['name'] in brand_names else 'do',
                }) for ds_brand in ds_brand_data]
            })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': wizard._name,
            'res_id': wizard.id,
            'target': 'new',
        }

    @api.multi
    def get_product_code_convert_func(self, client=False, from_datastore=True):
        u"""
        :param client: Connecteur ouvert vers la base centralisée.
        :param from_datastore: Si True, la conversion se fait depuis la base centralisée vers la base locale.
                               Si False, la conversion se fait depuis la base locale vers la base centralisée.
        :return: fonction de conversion entre la référence de l'article centralisé et la référence locale
        """
        self.ensure_one()
        if not client:
            client = self.of_datastore_connect()
        ds_brand_obj = self.of_datastore_get_model(client, 'of.product.brand')
        brand_match = {brand.datastore_brand_id: brand for brand in self.brand_ids}
        ds_brands_data = self.of_datastore_read(ds_brand_obj, brand_match.keys(), ['code', 'use_prefix'])
        default_code_func = {}
        for ds_brand in ds_brands_data:
            brand = brand_match[ds_brand['id']]
            brand_from = ds_brand if from_datastore else brand
            brand_to = brand if from_datastore else ds_brand
            if brand_from['use_prefix'] and brand_to['use_prefix'] and brand_from['code'] == brand_to['code']:
                # Le préfixe est le même : on ne va pas le retirer pour le remettre!
                default_code_func[brand] = lambda code: code
                continue
            if brand_to['use_prefix']:
                func = "lambda code: '%s_' + code" % brand_to['code']
            else:
                func = "lambda code: code"
            if brand_from['use_prefix']:
                func += '[%i:]' % (len(brand_from['code']) + 1)
            default_code_func[brand] = safe_eval(func)
        return default_code_func

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        if fields and all(field in ('brand_ids', 'db_name') for field in fields):
            # Un utilisateur non admin ne doit avoir accès qu'aux marques et db_name du connecteur TC
            # (surtout pas aux accès login/password)
            self = self.sudo()
        return super(OfDatastoreSupplier, self).read(fields, load=load)
