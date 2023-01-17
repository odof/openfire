# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
from simplejson import JSONDecodeError

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OFDatastoreBrandAskWizard(models.TransientModel):
    _name = 'of.datastore.brand.ask.wizard'

    fee = fields.Float(related='datastore_brand_id.fee', string=u"Surcoût", readonly=True)
    fee2 = fields.Float(related='datastore_brand_id.fee', string=u"Surcoût", readonly=True)
    action = fields.Selection(
        selection=[('connect', u"Connexion"), ('disconnect', u"Déconnexion"), ('cancel', u"Annulation")],
        required=True)
    brand_id = fields.Many2one(
        comodel_name='of.product.brand', related="datastore_brand_id.brand_id",
        compute_sudo=True, string=u"Marque à associer")
    datastore_brand_id = fields.Many2one(
        comodel_name='of.datastore.brand', string=u"Marque du tarif centralisé", required=True, ondelete='cascade')

    # Champs relationnels pour faciliter la lecture en xmlrpc depuis la base de gestion OpenFire
    ds_brand_id = fields.Integer(related='datastore_brand_id.datastore_brand_id')
    ds_db_name = fields.Char(related='datastore_brand_id.db_name')

    @api.multi
    def action_process(self):
        # On transmet à la base de gestion de OpenFire qu'il y a une demande à traiter.
        # Cette base viendra directement chercher les informations du wizard en xmlrpc.
        # Il n'est ainsi pas possible de profiter de la route publique pour adresser une demande non légitime.
        openfire_url = self.env['ir.config_parameter'].get_param('of.openfire.database.url')
        response = requests.post(
            url=openfire_url + "/brand/request",
            params={'dbname': self._cr.dbname, 'request_id': self.id})
        if response.status_code != requests.codes.ok:
            try:
                message = response.json()
            except JSONDecodeError:
                message = ""
            raise UserError(_(u"Erreur lors du traitement de la demande : %s - %s") % (response.status_code, message))
