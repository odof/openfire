# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_geo_comment = fields.Text(
        string=u"Commentaire du client", help=u"Commentaire du client rempli lors de la prise de RDV en ligne")


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    website_create = fields.Boolean(string=u"Créé par le portail web")


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    website_create = fields.Boolean(string=u"Créé par le portail web")

    @api.multi
    def get_display_date(self):
        self.ensure_one();
        return fields.Date.from_string(self.date).strftime('%A %d %B')
