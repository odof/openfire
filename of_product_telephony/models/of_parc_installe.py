# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    is_telecom = fields.Boolean(string=u"Article Télécom", related='product_id.of_is_telecom')
    optical_fiber_type = fields.Selection(
        selection=[('ffth', u"FFTH (fiber to the home)"), ('ffto', u"FFTO (fiber to the office)")],
        string=u"Type de Fibre", related='product_id.of_optical_fiber_type')
    date_installation = fields.Date(string=u"Date de mise en service")
    cancel_date = fields.Date(
        string=u"Date de résiliation", help=u"Date de fin de ligne de contrat, fin de ligne d’abonnement")
    provider_ref = fields.Char(string=u"Référence opérateur")
    provider_id = fields.Many2one(
        comodel_name='res.partner', string=u"Opérateur",
        help=u"Orange, SFR, etc choisi par le client pour la ligne téléphone. "
             u"Choisi par MCT selon la disponibilité pour l’accès internet")
    power_outlet_ref = fields.Char(
        string=u"Référence prise", help=u"Identifiant référence opérateur bis")
    concentration_point = fields.Char(
        string=u"Position au PM",
        help=u"Codification qui indique l’emplacement de l’armoire de rue (point de mutualisation) "
             u"sur les trottoirs ou raccorder la fibre.")
    secondary_site_id = fields.Many2one(
        comodel_name='res.partner', string=u"Site B du lien",
        help=u"Permet de définir une zone avec un site principal et un site secondaire")
