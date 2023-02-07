# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
from simplejson import JSONDecodeError

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError


class OFDatastoreBrand(models.Model):
    _name = 'of.datastore.brand'
    _description = u"Marques accessibles via le tarif centralisé"
    _inherit = 'mail.thread'
    _order = 'name'

    datastore_brand_id = fields.Integer(string=u"Centralized ID", help="ID de la marque sur la base fournisseur")
    db_name = fields.Char(string="Base fournisseur")
    name = fields.Char(string=u"Libellé", required=True)
    logo = fields.Binary(string=u"Logo", attachment=True)
    update_date = fields.Date(string=u"Date de mise à jour", readonly=True)
    is_partner_managed = fields.Boolean(
        string=u"Fournisseur partenaire",
        help=u"Si le fournisseur est partenaire, il est responsable de la mise à jour de ses tarifs.\n"
             u"Dans le cas contraire, la mise à jour est réalisée par OpenFire et entraîne un surcoût.")
    fee = fields.Float(string=u"Surcoût (mensuel)")
    state = fields.Selection(
        selection=[
            ('available', u"Disponible"),
            ('pending_in', u"Demande de connexion en attente"),
            ('connected', u"Connecté"),
            ('pending_out', u"Demande de déconnexion en attente"),
        ],
        string=u"État", required=True, track_visibility='onchange')
    brand_id = fields.Many2one(
        comodel_name='of.product.brand', string=u"Marque associée", ondelete='restrict')

    @api.multi
    def write(self, vals):
        if self._uid != SUPERUSER_ID:
            if any(field in ('is_partner_managed', 'fee', 'name') for field in vals):
                raise UserError(_(u"Vous essayez de modifier des champs protégés"))
        return super(OFDatastoreBrand, self).write(vals)

    @api.model
    def update_brands(self):
        """
        Fonction appelée par cron
        """
        openfire_url = self.env['ir.config_parameter'].get_param('of.openfire.database.url')
        last_update = self.env['ir.config_parameter'].get_param('of.datastore.brand.last.update')
        response = requests.post(
            url=openfire_url + "/brand/list",
            params={'dbname': self._cr.dbname, 'since_dt': last_update or ''})
        if response.status_code != requests.codes.ok:
            try:
                message = response.json()
            except JSONDecodeError:
                message = ""
            raise UserError(_(u"Erreur lors du traitement de la demande : %s - %s") % (response.status_code, message))
        data = response.json()
        local_brands_dict = {
            (brand.db_name, brand.datastore_brand_id): brand
            for brand in self.search([])
        }
        for brand_data in data:
            local_brand = local_brands_dict.pop((brand_data['db_name'], brand_data['datastore_brand_id']), False)
            if 'name' in brand_data:
                if local_brand:
                    local_brand.write(brand_data)
                else:
                    brand_data['state'] = 'available'
                    self.create(brand_data)
        to_remove_ids = [brand.id for brand in local_brands_dict.itervalues()]
        if to_remove_ids:
            self.browse(to_remove_ids).unlink()

        self.env['ir.config_parameter'].set_param('of.datastore.brand.last.update', fields.Date.today())

        # S'il existe des marques connectées mais non liées à une marque de la base de gestion, on tente de les associer
        for brand in self.env['of.product.brand'].search(
                [('datastore_brand_id', '!=', False), ('datastore_brand_request_ids', '=', False)]):
            datastore_brand = self.search(
                [('db_name', '=', brand.datastore_supplier_id.db_name),
                 ('datastore_brand_id', '=', brand.datastore_brand_id)],
                limit=1)
            if datastore_brand:
                if datastore_brand.brand_id:
                    # :todo: remplacer ce raise par un send_error à destination de la base de gestion ?
                    raise UserError(
                        _(u"Une marque centralisée a plusieurs correspondances possibles : %s vs %s et %s")
                        % (datastore_brand.name, datastore_brand.brand_id.name, brand.name))
                datastore_brand.write({
                    'brand_id': brand.id,
                    'state': 'connected',
                })

    @api.multi
    def action_granted(self, login, password):
        """
        Action appelée par le compte admin pour accepter la connexion de la marque au tarif centralisé
        """
        self.ensure_one()
        if not self.brand_id:
            raise UserError(_(u"La demande n'est pas associée à une marque"))
        if self.brand_id.datastore_supplier_id:
            raise UserError(_(u"La marque est déjà connectée"))

        supplier_obj = self.env['of.datastore.supplier']
        supplier = supplier_obj.search([('db_name', '=', self.db_name)])
        if not supplier:
            supplier = supplier_obj.create({
                'db_name': self.db_name,
                'server_address': 'https://' + self.db_name + '.openfire.fr',
                'login': login,
                'password': password,
            })

        self.brand_id.write({
            'datastore_supplier_id': supplier.id,
            'datastore_brand_id': self.datastore_brand_id,
        })

        # On vide le champ of_datastore_res_id des articles de la marque nouvellement liée au TC.
        self.env['product.product']\
            .search([('brand_id', '=', self.brand_id.id), ('of_datastore_res_id', '!=', False)])\
            .write({'of_datastore_res_id': False})
        self.env['product.template']\
            .search([('brand_id', '=', self.brand_id.id), ('of_datastore_res_id', '!=', False)])\
            .write({'of_datastore_res_id': False})

        self.write({'state': 'connected'})
        return True

    @api.multi
    def action_revoked(self):
        """
        Action appelée par le compte admin pour couper la connexion de la marque au tarif centralisé
        """
        brands = self.mapped('brand_id')
        brands.write({
            'datastore_supplier_id': False,
            'datastore_brand_id': False,
        })
        self.env['product.product']\
            .search([('brand_id', 'in', brands.ids), ('of_datastore_res_id', '!=', False)])\
            .write({'of_datastore_res_id': False})
        self.env['product.template']\
            .search([('brand_id', 'in', brands.ids), ('of_datastore_res_id', '!=', False)])\
            .write({'of_datastore_res_id': False})
        self.write({'state': 'available'})
        return True
