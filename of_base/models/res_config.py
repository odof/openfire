# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BaseConfiguration(models.TransientModel):
    _inherit = 'base.config.settings'

    @api.model
    def get_default_alias_domain(self, fields):
        # Modification de la fonction odoo (module mail)
        # Si aucun "mail.catchall.domain", on ne veut pas forcer une valeur par défaut dans ce wizard de configuration
        alias_domain = self.env["ir.config_parameter"].get_param("mail.catchall.domain", default=None)
        return {'alias_domain': alias_domain or False}


class OFConnectorConfigSettings(models.TransientModel):
    _name = 'of.connector.config.settings'
    _inherit = 'res.config.settings'
    _description = 'Configuration des connecteurs'

    company_id = fields.Many2one(
        comodel_name='res.company', string="Company", required=True,
        default=lambda self: self.env.user.company_id)
