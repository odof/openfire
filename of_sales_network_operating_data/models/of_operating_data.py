# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
import logging

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class OFOperatingData(models.Model):
    _name = 'of.operating.data'
    _description = u"Données d'exploitation du réseau"
    _order = 'period desc, database'

    origin = fields.Selection(
        selection=[('manual', u"Manuelle"), ('connector', u"Connecteur")], string=u"Méthode de création", required=True,
        default='manual')
    database = fields.Char(string=u"Base de données")
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Magasin", required=True)
    period_type = fields.Selection(
        selection=[('day', u"Jour"), ('week', u"Semaine"), ('month', u"Mois")], string=u"Type de période")
    period = fields.Date(string=u"Période", default=fields.Date.today, required=True)
    contact_nb = fields.Integer(string=u"Nombre de contacts")
    opportunity_nb = fields.Integer(string=u"Nombre d'opportunités")
    digital_opportunity_nb = fields.Integer(string=u"Nombre d'opportunités digitales")
    quotation_nb = fields.Integer(string=u"Nombre de devis")
    digital_quotation_nb = fields.Integer(string=u"Nombre de devis digitaux")
    quotation_amount = fields.Float(string=u"Montant de devis généré")
    digital_quotation_amount = fields.Float(string=u"Montant de devis digitaux généré")
    current_quotation_amount = fields.Float(string=u"Montant de devis en cours")
    sale_nb = fields.Integer(string=u"Nombre de ventes")
    digital_sale_nb = fields.Integer(string=u"Nombre de ventes digitales")
    turnover = fields.Float(string=u"CA €")
    digital_turnover = fields.Float(string=u"CA digital €")
    margin = fields.Float(string=u"Marge €")
    margin_perc = fields.Float(string=u"Marge %")
    average_cart = fields.Float(string=u"Panier moyen €")
    digital_average_cart = fields.Float(string=u"Panier moyen digital €")
    invoiced_turnover = fields.Float(string=u"CA facturé €")
    deposit_excl_invoiced_turnover = fields.Float(string=u"CA facturé € (hors acompte)")

    _sql_constraints = [
        ('period_uniq',
         'unique (partner_id, period_type, period)',
         u"Vous ne pouvez pas créer deux entrées sur la même période pour le même magasin.")
    ]

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = "%s - %s" % (rec.partner_id.name, fields.Date.from_string(rec.period).strftime('%d/%m/%Y'))
            res.append((rec.id, name))
        return res

    @api.model
    def trigger_esb(self, period_type, force_date=False):
        url = self.env['ir.values'].sudo().get_default('of.sales.network.config.settings', 'esb_url')
        login = self.env['ir.values'].sudo().get_default('of.sales.network.config.settings', 'esb_login')
        password = self.env['ir.values'].sudo().get_default('of.sales.network.config.settings', 'esb_password')

        if not url:
            _logger.info(u"Operating Data ESB Cron - ERREUR : L'URL de l'ESB est manquante dans la configuration.")
            return False

        if not login:
            _logger.info(
                u"Operating Data ESB Cron - ERREUR : L'identifiant de connexion à l'ESB est manquant dans "
                "la configuration.")
            return False

        if not password:
            _logger.info(
                u"Operating Data ESB Cron - ERREUR : Le mot de passe de connexion à l'ESB est manquant dans "
                "la configuration.")
            return False

        period_date = False
        if force_date:
            period_date = force_date
        elif period_type == 'day':
            period_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        elif period_type == 'week':
            period_date = (date.today() - timedelta(days=date.today().weekday()) + timedelta(weeks=-1)).\
                strftime("%Y-%m-%d")
        elif period_type == 'month':
            period_date = (date.today() + relativedelta(day=1, months=-1)).strftime("%Y-%m-%d")
        else:
            _logger.info(u"Operating Data ESB Cron - ERREUR : Paramètre type de période incorrect.")
            return False

        data = {
            'user': login,
            'password': password,
            'period_type': period_type,
            'period': period_date,
        }

        response = requests.post(url, data=data)
        response_data = response.json()

        if response_data.get('code', '') != 200:
            _logger.info(u"Operating Data ESB Cron - ERREUR : %s" % response_data.get('res', ''))
            return False

        _logger.info(u"Operating Data ESB Cron - OK - UUID : %s" % response_data.get('uuid', ''))
        return True
