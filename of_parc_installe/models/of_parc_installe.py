# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api

class of_parc_installe(models.Model):
    """Parc installé"""

    _name = 'of.parc.installe'
    _description = "Parc installé"

    name = fields.Char("No de série", size=64, required=False)
    date_service = fields.Date("Date vente", required=False)
    date_installation = fields.Date("Date d'installation", required=False)
    date_fin_garantie = fields.Date(string="Fin de garantie")
    product_id = fields.Many2one('product.product', 'Produit', required=True, ondelete='restrict')
    product_category_id = fields.Char(u'Famille', related="product_id.categ_id.name", readonly=True)
    client_id = fields.Many2one('res.partner', 'Client', required=True, domain="[('parent_id','=',False)]", ondelete='restrict')
    client_name = fields.Char(related='client_id.name')  # for map view
    client_mobile = fields.Char(related='client_id.mobile')  # for map view
    site_adresse_id = fields.Many2one('res.partner', 'Site installation', required=False, domain="['|',('parent_id','=',client_id),('id','=',client_id)]", ondelete='restrict')
    revendeur_id = fields.Many2one('res.partner', 'Revendeur', required=False,  domain="[('of_revendeur','=',True)]", ondelete='restrict')
    installateur_id = fields.Many2one('res.partner', 'Installateur', required=False, domain="[('of_installateur','=',True)]", ondelete='restrict')
    installateur_adresse_id = fields.Many2one('res.partner', 'Adresse installateur', required=False, domain="['|',('parent_id','=',installateur_id),('id','=',installateur_id)]", ondelete='restrict')
    note = fields.Text('Note')
    tel_site_id = fields.Char(u"Téléphone site installation", related='site_adresse_id.phone', readonly=True)
    street_site_id = fields.Char(u'Adresse', related="site_adresse_id.street", readonly=True)
    street2_site_id = fields.Char(u'Complément adresse', related="site_adresse_id.street2", readonly=True)
    zip_site_id = fields.Char(u'Code postal', related="site_adresse_id.zip", readonly=True, store=True)
    city_site_id = fields.Char(u'<Ville', related="site_adresse_id.city", readonly=True)
    country_site_id = fields.Many2one('res.country', u'Pays', related="site_adresse_id.country_id", readonly=True)
    no_piece = fields.Char(u'N° pièce', size=64, required=False)
    project_issue_ids = fields.One2many('project.issue', 'of_produit_installe_id', 'SAV')
    active = fields.Boolean(string=u'Actif', default=True)

    # Champs ajoutés pour la vue map
    geo_lat = fields.Float('geo_lat', compute='_compute_geo')
    geo_lng = fields.Float('geo_lng', compute='_compute_geo')
    precision = fields.Selection([
        ('manual', "Manuel"),
        ('high', "Haut"),
        ('medium', "Moyen"),
        ('low', "Bas"),
        ('no_address', u"--"),
        ('unknown', u"Indéterminé"),
        ('not_tried', u"Pas tenté"),
        ], default='not_tried', string='precision', compute='_compute_geo')

    _sql_constraints = [('no_serie_uniq', 'unique(name)', u"Ce numéro de série est déjà utilisé et doit être unique.")]

    @api.multi
    @api.depends('client_id', 'site_adresse_id')
    def _compute_geo(self):
        for produit_installe in self:
            if produit_installe.site_adresse_id:
                produit_installe.geo_lat = produit_installe.site_adresse_id.geo_lat
                produit_installe.geo_lng = produit_installe.site_adresse_id.geo_lng
                produit_installe.precision = produit_installe.site_adresse_id.precision
            else:
                produit_installe.geo_lat = produit_installe.client_id.geo_lat
                produit_installe.geo_lng = produit_installe.client_id.geo_lng
                produit_installe.precision = produit_installe.client_id.precision

    @api.model
    def action_creer_sav(self):
        res = {
            'name': 'SAV',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        active_ids = self._context.get('active_ids')
        if active_ids:
            parc_installe = self.browse(active_ids[0])
            if parc_installe.client_id:
                res['context'] = {'default_partner_id': parc_installe.client_id.id,
                                  'default_of_produit_installe_id': parc_installe.id,
                                  'default_of_type': 'di'}
        return res

class res_partner(models.Model):
    _inherit = "res.partner"

    of_revendeur = fields.Boolean('Revendeur', help="Cocher cette case si ce partenaire est un revendeur.")
    of_installateur = fields.Boolean('Installateur', help="Cocher cette case si ce partenaire est un installateur.")
    of_parc_installe_count = fields.Integer("Parc installé", compute='_compute_of_parc_installe_count')

    @api.multi
    def _compute_of_parc_installe_count(self):
        for partner in self:
            partner.of_parc_installe_count = self.env['of.parc.installe'].search_count([('client_id', '=', partner.id)])

class project_issue(models.Model):
    _name = 'project.issue'
    _inherit = ['project.issue', 'of.map.view.mixin']

#     def _get_product_sav_ids(self, cr, uid, ids, context={}):
#         return self.pool['project.issue'].search(cr, uid, [('product_name_id','in',ids)], context=context)

    def _search_of_parc_installe_site_adresse(self, operator, value):
        "Permet la recherche sur l'adresse d'installation de la machine depuis un SAV"
        # Deux cas :
        # - Rechercher tous les SAV qui ont une machine installée mais dont l'adresse d'installation n'est soit pas renseignée, soit vide (1er cas du if)
        # - Recherche classique sur sur la rue, complément adresse, CP ou la ville (2e cas du if).

        cr = self._cr
        if value == '' and operator == '=': # Si l'opérateur est = et value vide, c'est qu'on vient du filtre personnalisée rechercher les adresses d'installation non renseignée ou vide.
            value = '%%%s%%' % value
            cr.execute("SELECT project_issue.id AS id\n"
                "FROM project_issue\n"
                "INNER JOIN of_parc_installe ON of_parc_installe.id = project_issue.of_produit_installe_id\n"
                "LEFT JOIN res_partner ON res_partner.id = of_parc_installe.site_adresse_id\n"
                "WHERE (res_partner.street = '' OR res_partner.street is null)\n"
                "  AND (res_partner.street2 = '' OR res_partner.street2 is null)\n"
                "  AND (res_partner.zip = '' OR res_partner.zip is null)\n"
                "  AND (res_partner.city = '' OR res_partner.city is null)")
        else:
            value = '%%%s%%' % value
            cr.execute("SELECT project_issue.id AS id\n"
               "FROM res_partner, of_parc_installe, project_issue\n"
               "WHERE (res_partner.street ilike %s OR res_partner.street2 ilike %s OR res_partner.zip ilike %s OR res_partner.city ilike %s)\n"
               "  AND res_partner.id = of_parc_installe.site_adresse_id\n"
               "  AND of_parc_installe.id = project_issue.of_produit_installe_id", (value, value, value, value))

        return [('id', 'in', cr.fetchall())]


    of_produit_installe_id = fields.Many2one('of.parc.installe', u'Produit installé', ondelete='restrict', readonly=False)
    product_name_id = fields.Many2one('product.product', u'Désignation', ondelete='restrict')
    product_category_id = fields.Char(u'Famille', related="product_name_id.categ_id.name", readonly=True, store=True)
    of_parc_installe_client_nom = fields.Char(u'Client produit installé', related="of_produit_installe_id.client_id.name", readonly=True)
    of_parc_installe_client_adresse = fields.Char(u'Adresse client', related="of_produit_installe_id.client_id.contact_address", readonly=True)
    of_parc_installe_site_nom = fields.Char(u"Lieu d'installation", related="of_produit_installe_id.site_adresse_id.name", readonly=True)
    of_parc_installe_site_zip = fields.Char('Code Postal', size=24, related='of_produit_installe_id.site_adresse_id.zip')
    of_parc_installe_site_city = fields.Char('Ville', related='of_produit_installe_id.site_adresse_id.city')
    of_parc_installe_site_adresse = fields.Char(u"Adresse d'installation", related="of_produit_installe_id.site_adresse_id.contact_address", search='_search_of_parc_installe_site_adresse', readonly=True)
    of_parc_installe_note = fields.Text('Note produit installé', related="of_produit_installe_id.note", readonly=True)
    of_parc_installe_fin_garantie = fields.Date(string='Fin de garantie', related="of_produit_installe_id.date_fin_garantie", readonly=True)

    # Champs ajoutés pour la vue map
    of_geo_lat = fields.Float(related='of_produit_installe_id.geo_lat')
    of_geo_lng = fields.Float(related='of_produit_installe_id.geo_lng')
    of_precision = fields.Selection(related='of_produit_installe_id.precision')

    of_color_map = fields.Char(string="Couleur du marqueur", compute="_compute_of_color_map")

    @api.multi
    @api.depends('date_deadline')
    def _compute_of_color_map(self):
        date_today = fields.Date.from_string(fields.Date.today())

        for issue in self:
            color = 'gray'
            if issue.date_deadline:
                date_deadline = fields.Date.from_string(issue.date_deadline)
                if date_deadline > date_today + timedelta(days=15):  # deadline dans plus de 2 semaines
                    color = "blue"
                elif date_deadline >= date_today:  # deadline dans moins de 2 semaines
                    color = "orange"
                else:  # deadline passée
                    color = "red"
            issue.of_color_map = color

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

    @api.onchange('of_produit_installe_id')
    def on_change_of_produit_installe_id(self):
        # Si le no de série est saisi, on met le produit du no de série du parc installé.
        if self.of_produit_installe_id:
            parc = self.env['of.parc.installe'].browse([self.of_produit_installe_id.id])
            if parc and parc.product_id:
                self.product_name_id = parc.product_id.id
#                 self.write({
#                     'product_name_id': parc.product_id.id,
#                     'of_parc_installe_client_nom': parc.client_id.name,
#                     'of_parc_installe_client_adresse': parc.client_id.contact_address,
#                     'of_parc_installe_site_nom': parc.site_adresse_id.name,
#                     'of_parc_installe_site_adresse': parc.site_adresse_id.contact_address,
#                     'of_parc_installe_note': parc.note})

    @api.onchange('product_name_id')
    def on_change_product_name_id(self):
        # Si un no de série est saisie, on force le produit lié au no de série.
        # Si pas de no de série, on laisse la possibilité de choisir un article
        if self.of_produit_installe_id: # Si no de série existe, on récupère l'article associé
            self.on_change_of_produit_installe_id()

