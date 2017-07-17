# -*- coding: utf-8 -*-

from odoo import models, fields, api

class of_parc_installe(models.Model):
    """Parc installé"""

    _name = 'of.parc.installe'
    _description = "Parc installé"

    name = fields.Char("No de série", size=64, required=False)
    date_service = fields.Date("Date vente", required=False)
    date_installation = fields.Date("Date d'installation", required=False)
    product_id = fields.Many2one('product.product', 'Produit', required=True, ondelete='restrict')
    product_category_id = fields.Char(u'Famille', related="product_id.categ_id.name", readonly=True)
    client_id = fields.Many2one('res.partner', 'Client', required=True, domain="[('parent_id','=',False)]", ondelete='restrict')
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

    _sql_constraints = [('no_serie_uniq', 'unique(name)', u"Ce numéro de série est déjà utilisé et doit être unique.")]

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


class project_issue(models.Model):
    _inherit = "project.issue"

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
    of_parc_installe_site_adresse = fields.Char(u"Adresse d'installation", related="of_produit_installe_id.site_adresse_id.contact_address", search='_search_of_parc_installe_site_adresse', readonly=True)
    of_parc_installe_note = fields.Text('Note produit installé', related="of_produit_installe_id.note", readonly=True)


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

