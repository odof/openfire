# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFConnectorConfigSettings(models.TransientModel):
    _inherit = 'of.connector.config.settings'

    of_poujoulat_host = fields.Char(
        string=u"Adresse du serveur", help=u"Url poujoulat")
    of_poujoulat_redirect = fields.Char(string=u"Url de redirection")
    of_poujoulat_partner_ids = fields.Many2many(
        comodel_name='res.partner', relation='of_connector_config_poujoulat_partners_rel',
        string=u"Fournisseurs Poujoulat")
    of_poujoulat_brand_ids = fields.Many2many(
        comodel_name='of.product.brand', relation='of_connector_config_poujoulat_brands_rel',
        string=u"Marques Poujoulat")

    @api.multi
    def set_of_poujoulat_host_defaults(self):
        host = self.of_poujoulat_host
        if host and not host.endswith('/'):
            host = u"%s/" % host
        return self.env['ir.values'].sudo().set_default('of.connector.config.settings', 'of_poujoulat_host', host)

    @api.multi
    def set_of_poujoulat_redirect_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_poujoulat_redirect', self.of_poujoulat_redirect)

    @api.multi
    def set_of_poujoulat_partner_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_poujoulat_partner_ids', self.of_poujoulat_partner_ids.ids)

    @api.multi
    def set_of_poujoulat_brand_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.connector.config.settings', 'of_poujoulat_brand_ids', self.of_poujoulat_brand_ids.ids)
