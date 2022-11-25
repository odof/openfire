# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api


class ProjectIssue(models.Model):
    _name = 'project.issue'
    _inherit = ['project.issue', 'of.map.view.mixin']

    def _search_of_parc_installe_site_adresse(self, operator, value):
        """Permet la recherche sur l'adresse d'installation de la machine depuis un SAV"""
        # Deux cas :
        # - Rechercher tous les SAV qui ont une machine installée mais dont l'adresse d'installation
        #   n'est soit pas renseignée, soit vide (1er cas du if)
        # - Recherche classique sur sur la rue, complément adresse, CP ou la ville (2e cas du if).

        cr = self._cr
        if value == '' and operator == '=':
            # Si l'opérateur est = et value vide, c'est qu'on vient du filtre personnalisé
            # -> rechercher les adresses d'installation non renseignées ou vides.
            cr.execute(
                "SELECT project_issue.id AS id\n"
                "FROM project_issue\n"
                "INNER JOIN of_parc_installe ON of_parc_installe.id = project_issue.of_produit_installe_id\n"
                "LEFT JOIN res_partner ON res_partner.id = of_parc_installe.site_adresse_id\n"
                "WHERE (res_partner.street = '' OR res_partner.street is null)\n"
                "  AND (res_partner.street2 = '' OR res_partner.street2 is null)\n"
                "  AND (res_partner.zip = '' OR res_partner.zip is null)\n"
                "  AND (res_partner.city = '' OR res_partner.city is null)")
        else:
            value = '%%%s%%' % value
            cr.execute(
                "SELECT project_issue.id AS id\n"
                "FROM res_partner, of_parc_installe, project_issue\n"
                "WHERE (res_partner.street ilike %s OR res_partner.street2 ilike %s"
                "       OR res_partner.zip ilike %s OR res_partner.city ilike %s)\n"
                "  AND res_partner.id = of_parc_installe.site_adresse_id\n"
                "  AND of_parc_installe.id = project_issue.of_produit_installe_id", (value, value, value, value))

        return [('id', 'in', cr.fetchall())]

    of_produit_installe_id = fields.Many2one(
        comodel_name='of.parc.installe', string=u"Produit installé", ondelete='restrict', readonly=False)
    product_name_id = fields.Many2one(comodel_name='product.product', string=u"Désignation", ondelete='restrict')
    product_category_id = fields.Many2one(
        comodel_name='product.category', string=u"Famille", related='product_name_id.categ_id', readonly=True,
        store=True)
    of_parc_installe_client_nom = fields.Char(
        string=u"Client produit installé", related='of_produit_installe_id.client_id.name', readonly=True)
    of_parc_installe_client_adresse = fields.Char(
        string=u"Adresse client", related='of_produit_installe_id.client_id.contact_address', readonly=True)
    of_parc_installe_site_nom = fields.Char(
        string=u"Lieu d'installation", related='of_produit_installe_id.site_adresse_id.name', readonly=True)
    of_parc_installe_site_zip = fields.Char(
        string=u"Code Postal", size=24, related='of_produit_installe_id.site_adresse_id.zip')
    of_parc_installe_site_city = fields.Char(
        string=u"Ville", related='of_produit_installe_id.site_adresse_id.city')
    of_parc_installe_site_adresse = fields.Char(
        string=u"Adresse d'installation", related='of_produit_installe_id.site_adresse_id.contact_address',
        search='_search_of_parc_installe_site_adresse', readonly=True)
    of_parc_installe_note = fields.Text(
        string=u"Note produit installé", related='of_produit_installe_id.note', readonly=True)
    of_parc_installe_fin_garantie = fields.Date(
        string=u"Fin de garantie", related='of_produit_installe_id.date_fin_garantie', readonly=True)
    of_parc_installe_lieu_id = fields.Many2one(
        comodel_name='res.partner', string=u"Lieu du produit installé", compute='_compute_of_parc_installe_lieu_id')
    of_parc_installe_client_id = fields.Many2one(
        comodel_name='res.partner', string=u"Client du produit installé", compute='_compute_of_parc_installe_lieu_id')

    # Champs ajoutés pour la vue map
    of_geo_lat = fields.Float(related='of_produit_installe_id.geo_lat')
    of_geo_lng = fields.Float(related='of_produit_installe_id.geo_lng')
    of_precision = fields.Selection(related='of_produit_installe_id.precision')

    of_color_map = fields.Char(string=u"Couleur du marqueur", compute='_compute_of_color_map')

    # @api.depends

    @api.multi
    @api.depends('of_produit_installe_id', 'of_produit_installe_id.client_id', 'of_produit_installe_id.site_adresse_id')
    def _compute_of_parc_installe_lieu_id(self):
        for issue in self:
            if issue.of_produit_installe_id:
                issue.of_parc_installe_client_id = issue.of_produit_installe_id.client_id.id
                if issue.of_produit_installe_id.site_adresse_id:
                    issue.of_parc_installe_lieu_id = issue.of_produit_installe_id.site_adresse_id.id
                else:
                    issue.of_parc_installe_lieu_id = issue.of_produit_installe_id.client_id.id

    @api.multi
    @api.depends('date_deadline')
    def _compute_of_color_map(self):
        date_today = fields.Date.from_string(fields.Date.today())

        for issue in self:
            color = 'gray'
            if issue.date_deadline:
                date_deadline = fields.Date.from_string(issue.date_deadline)
                if date_deadline > date_today + timedelta(days=15):
                    # deadline dans plus de 2 semaines
                    color = "blue"
                elif date_deadline >= date_today:
                    # deadline dans moins de 2 semaines
                    color = "orange"
                else:
                    # deadline passée
                    color = "red"
            issue.of_color_map = color

    # @api.onchange

    @api.onchange('of_produit_installe_id')
    def onchange_of_produit_installe_id(self):
        # Si le no de série est saisi, on met le produit du no de série du parc installé.
        if self.of_produit_installe_id:
            parc = self.env['of.parc.installe'].browse([self.of_produit_installe_id.id])
            if parc and parc.product_id:
                self.product_name_id = parc.product_id.id

    @api.onchange('product_name_id')
    def onchange_product_name_id(self):
        # Si un no de série est saisie, on force le produit lié au no de série.
        # Si pas de no de série, on laisse la possibilité de choisir un article
        if self.of_produit_installe_id:  # Si no de série existe, on récupère l'article associé
            self.onchange_of_produit_installe_id()

    @api.model
    def get_color_map(self):
        u"""
        fonction pour la légende de la vue map
        """
        return {
            'title': u"Échéance",
            'values': (
                {'label': u'Aucune', 'value': 'gray'},
                {'label': u"Plus de 15 jours", 'value': 'blue'},
                {'label': u'Moins de 15 jours', 'value': 'orange'},
                {'label': u'En retard', 'value': 'red'},
            )
        }
