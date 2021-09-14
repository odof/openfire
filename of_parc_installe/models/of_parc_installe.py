# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api
from odoo.addons.of_geolocalize.models.of_geo import GEO_PRECISION


class OFParcInstalle(models.Model):
    """Parc installé"""

    _name = 'of.parc.installe'
    _description = u"Parc installé"

    name = fields.Char(u"No de série", size=64, required=False, copy=False)
    date_service = fields.Date("Date vente", required=False)
    date_installation = fields.Date("Date d'installation", required=False)
    date_fin_garantie = fields.Date(string="Fin de garantie")
    product_id = fields.Many2one('product.product', 'Produit', required=True, ondelete='restrict')
    product_category_id = fields.Many2one('product.category', string=u'Catégorie')
    client_id = fields.Many2one(
        'res.partner', string='Client', required=True, domain="[('parent_id','=',False)]", ondelete='restrict')
    client_name = fields.Char(related='client_id.name')  # for map view
    client_mobile = fields.Char(related='client_id.mobile')  # for map view
    site_adresse_id = fields.Many2one(
        'res.partner', string='Site installation', required=False,
        domain="['|',('parent_id','=',client_id),('id','=',client_id)]", ondelete='restrict')
    revendeur_id = fields.Many2one(
        comodel_name='res.partner', string='Revendeur', required=False, ondelete='restrict')
    installateur_id = fields.Many2one(
        comodel_name='res.partner', string='Installateur', required=False, ondelete='restrict')
    installateur_adresse_id = fields.Many2one(
        'res.partner', string='Adresse installateur', required=False,
        domain="['|',('parent_id','=',installateur_id),('id','=',installateur_id)]", ondelete='restrict')
    note = fields.Text('Note')
    tel_site_id = fields.Char(u"Téléphone site installation", related='site_adresse_id.phone', readonly=True)
    street_site_id = fields.Char(u'Adresse', related="site_adresse_id.street", readonly=True)
    street2_site_id = fields.Char(u'Complément adresse', related="site_adresse_id.street2", readonly=True)
    zip_site_id = fields.Char(u'Code postal', related="site_adresse_id.zip", readonly=True, store=True)
    city_site_id = fields.Char(u'Ville', related="site_adresse_id.city", readonly=True)
    country_site_id = fields.Many2one('res.country', u'Pays', related="site_adresse_id.country_id", readonly=True)
    no_piece = fields.Char(u'N° pièce', size=64, required=False)
    project_issue_ids = fields.One2many('project.issue', 'of_produit_installe_id', 'SAV')
    active = fields.Boolean(string=u'Actif', default=True)
    brand_id = fields.Many2one('of.product.brand', string="Marque")
    modele = fields.Char(u'Modèle')
    installation = fields.Char(u"Type d'installation")
    conforme = fields.Boolean('Conforme', default=True)
    state = fields.Selection(
        selection=[
            ('neuf', 'Neuf'),
            ('bon', 'Bon'),
            ('usage', u'Usagé'),
            ('remplacer', u"À remplacer"),
        ], string=u'État', default="neuf")
    sale_order_ids = fields.Many2many('sale.order', string="Commandes")
    sale_order_amount = fields.Float(compute='_compute_links')
    account_invoice_ids = fields.Many2many('account.invoice', string="Factures")
    account_invoice_amount = fields.Float(compute='_compute_links')

    # Champs ajoutés pour la vue map
    geo_lat = fields.Float('geo_lat', compute='_compute_geo', store=True)
    geo_lng = fields.Float('geo_lng', compute='_compute_geo', store=True)
    precision = fields.Selection(
        GEO_PRECISION, default='not_tried', string='precision', compute='_compute_geo', store=True,
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")
    lot_id = fields.Many2one('stock.production.lot', string="Lot d'origine")

    technician_id = fields.Many2one(comodel_name='hr.employee', string=u"Technicien")

    # @api.depends

    @api.depends('sale_order_ids', 'account_invoice_ids')
    def _compute_links(self):
        for parc in self:
            parc.sale_order_amount = len(parc.sale_order_ids)
            parc.account_invoice_amount = len(parc.account_invoice_ids)

    @api.multi
    @api.depends('client_id', 'client_id.geo_lat', 'client_id.geo_lng', 'client_id.precision',
                 'site_adresse_id', 'site_adresse_id.geo_lat', 'site_adresse_id.geo_lng', 'site_adresse_id.precision')
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

    # @api.onchange

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.brand_id = self.product_id.brand_id
            self.product_category_id = self.product_id.categ_id

    @api.onchange('client_id')
    def _onchange_client_id(self):
        self.ensure_one()
        if self.client_id:
            self.site_adresse_id = self.client_id

    # Héritages

    @api.model
    def create(self, vals):
        parc = super(OFParcInstalle, self).create(vals)
        if parc.revendeur_id and not parc.revendeur_id.of_revendeur:
            parc.revendeur_id.of_revendeur = True
        if parc.installateur_id and not parc.installateur_id.of_installateur:
            parc.installateur_id.of_installateur = True
        return parc

    @api.multi
    def write(self, vals):
        res = super(OFParcInstalle, self).write(vals)
        if vals.get('revendeur_id'):
            non_revendeurs = self.mapped('revendeur_id').filtered(lambda p: not p.of_revendeur)
            non_revendeurs.write({'of_revendeur': True})
        if vals.get('installateur_id'):
            non_installateurs  = self.mapped('installateur_id').filtered(lambda p: not p.of_installateur)
            non_installateurs.write({'of_installateur': True})
        return res

    @api.multi
    def name_get(self):
        """
        Permet dans un SAV lors de la saisie du no de série d'une machine installée de proposer les machines
        du contact précédées d'une puce.
        Permet dans une DI de proposer les appareils d'une adresse différente entre parenthèses.
        """
        client_id = self._context.get('partner_id_no_serie_puce')
        if client_id:
            result = []
            for record in self:
                result.append((
                    record.id,
                    ("-> " if record.client_id.id == client_id else "")
                    + (record.name or u"(N° non renseigné)")
                    + " - " + record.client_id.display_name))
            return result
        address_id = self._context.get('address_prio_id')
        if address_id:
            result = []
            for parc in self:
                parc_address = parc.site_adresse_id or parc.client_id
                meme = parc_address and parc_address.id == address_id
                result.append((parc.id, "%s%s%s" % ('' if meme else '(', parc.name, '' if meme else ')')))
            return result
        return super(OFParcInstalle, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Permet dans un SAV lors de la saisie du no de série d'une machine installée de proposer les machines
        du contact en premier précédées d'une puce.
        Permet, dans une DI, de montrer en 1er les appareils de l'adresse, puis ceux du client et enfin les autres."""
        if self._context.get('partner_id_no_serie_puce'):
            client_id = self._context.get('partner_id_no_serie_puce')
            res = super(OFParcInstalle, self).name_search(name, [('client_id', '=', client_id)], operator, limit) or []
            limit = limit - len(res)
            res = [(parc[0], "-> " + parc[1]) for parc in res]
            res += super(OFParcInstalle, self).name_search(
                name, [('client_id', '!=', client_id)], operator, limit) or []
            return res
        if self._context.get('address_prio_id'):
            address_id = self._context.get('address_prio_id')
            args = args or []
            res = super(OFParcInstalle, self).name_search(
                name,
                args + [['site_adresse_id', '=', address_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(OFParcInstalle, self).name_search(
                name,
                args + ['|', ['site_adresse_id', '=', False], ['site_adresse_id', '!=', address_id],
                        ['client_id', '=', address_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(OFParcInstalle, self).name_search(
                name,
                args + ['|', ['site_adresse_id', '=', False], ['site_adresse_id', '!=', address_id],
                        ['client_id', '!=', address_id]],
                operator,
                limit) or []
            return res
        return super(OFParcInstalle, self).name_search(name, args, operator, limit)

    # Actions

    @api.multi
    def action_view_orders(self):
        action = self.env.ref('sale.action_quotations').read()[0]
        action['domain'] = [('id', 'in', self.sale_order_ids._ids)]
        return action

    @api.multi
    def action_view_invoices(self):
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['domain'] = [('id', 'in', self.account_invoice_ids._ids)]
        return action

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


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_revendeur = fields.Boolean('Revendeur', help="Cocher cette case si ce partenaire est un revendeur.")
    of_installateur = fields.Boolean('Installateur', help="Cocher cette case si ce partenaire est un installateur.")
    of_parc_installe_count = fields.Integer(string=u"Parc installé", compute='_compute_of_parc_installe_count')
    of_parc_installe_ids = fields.One2many('of.parc.installe', 'client_id', string=u"Parc installé")

    @api.multi
    def _compute_of_parc_installe_count(self):
        for partner in self:
            partner.of_parc_installe_count = self.env['of.parc.installe'].search_count([('client_id', '=', partner.id)])

    @api.multi
    def name_get(self):
        """
        Permet, dans un parc installé ou un pop-up de création de parc installé, de proposer les partenaires
        qui ne sont pas revendeurs/installateurs entre parenthèse. """
        revendeur_prio = self._context.get('of_revendeur_prio')
        installateur_prio = self._context.get('of_installateur_prio')
        if revendeur_prio or installateur_prio:
            result = []
            for employee in self:
                est_prio = revendeur_prio and employee.of_revendeur or installateur_prio and employee.of_installateur
                result.append((employee.id, "%s%s%s" % ('' if est_prio else '(',
                                                        employee.name,
                                                        '' if est_prio else ')')))
            return result
        return super(ResPartner, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un parc installé de proposer en premier les partenaires revendeurs/installateurs"""
        champ_prio = ''
        if self._context.get('of_revendeur_prio'):
            champ_prio = 'of_revendeur'
        elif self._context.get('of_installateur_prio'):
            champ_prio = 'of_installateur'
        if champ_prio:
            args = args or []
            res = super(ResPartner, self).name_search(
                name,
                args + [[champ_prio, '=', True]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(ResPartner, self).name_search(
                name,
                args + [[champ_prio, '=', False]],
                operator,
                limit) or []
            return res
        return super(ResPartner, self).name_search(name, args, operator, limit)


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
        'of.parc.installe', u'Produit installé', ondelete='restrict', readonly=False)
    product_name_id = fields.Many2one('product.product', u'Désignation', ondelete='restrict')
    product_category_id = fields.Many2one(
        'product.category', string=u'Famille', related="product_name_id.categ_id", readonly=True, store=True)
    of_parc_installe_client_nom = fields.Char(
        u'Client produit installé', related="of_produit_installe_id.client_id.name", readonly=True)
    of_parc_installe_client_adresse = fields.Char(
        u'Adresse client', related="of_produit_installe_id.client_id.contact_address", readonly=True)
    of_parc_installe_site_nom = fields.Char(
        u"Lieu d'installation", related="of_produit_installe_id.site_adresse_id.name", readonly=True)
    of_parc_installe_site_zip = fields.Char(
        'Code Postal', size=24, related='of_produit_installe_id.site_adresse_id.zip')
    of_parc_installe_site_city = fields.Char(
        'Ville', related='of_produit_installe_id.site_adresse_id.city')
    of_parc_installe_site_adresse = fields.Char(
        u"Adresse d'installation", related="of_produit_installe_id.site_adresse_id.contact_address",
        search='_search_of_parc_installe_site_adresse', readonly=True)
    of_parc_installe_note = fields.Text(
        u'Note produit installé', related="of_produit_installe_id.note", readonly=True)
    of_parc_installe_fin_garantie = fields.Date(
        string='Fin de garantie', related="of_produit_installe_id.date_fin_garantie", readonly=True)
    of_parc_installe_lieu_id = fields.Many2one(
        'res.partner', string=u"lieu du produit installé", compute="_compute_of_parc_installe_lieu_id")
    of_parc_installe_client_id = fields.Many2one(
        'res.partner', string=u"Client du produit installé", compute="_compute_of_parc_installe_lieu_id")

    # Champs ajoutés pour la vue map
    of_geo_lat = fields.Float(related='of_produit_installe_id.geo_lat')
    of_geo_lng = fields.Float(related='of_produit_installe_id.geo_lng')
    of_precision = fields.Selection(related='of_produit_installe_id.precision')

    of_color_map = fields.Char(string="Couleur du marqueur", compute="_compute_of_color_map")

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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_parc_installe_ids = fields.Many2many('of.parc.installe', string=u'Parcs installés')
    of_parc_count = fields.Integer(compute='_compute_parc_count')

    @api.multi
    def action_view_parc_installe(self):
        action = self.env.ref('of_parc_installe.action_view_of_parc_installe_sale').read()[0]
        action['domain'] = [('id', 'in', self.of_parc_installe_ids._ids)]
        return action

    @api.depends('of_parc_installe_ids')
    def _compute_parc_count(self):
        for order in self:
            order.of_parc_count = len(order.of_parc_installe_ids)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_parc_installe_ids = fields.Many2many('of.parc.installe', string=u'Parcs installés')
    of_parc_count = fields.Integer(compute='_compute_parc_count')

    @api.multi
    def action_view_parc_installe(self):
        action = self.env.ref('of_parc_installe.action_view_of_parc_installe_sale').read()[0]
        action['domain'] = [('id', 'in', self.of_parc_installe_ids._ids)]
        return action

    @api.depends('of_parc_installe_ids')
    def _compute_parc_count(self):
        for invoice in self:
            invoice.of_parc_count = len(invoice.of_parc_installe_ids)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_transfer(self):
        u"""
        Créé automatiquement un parc installé pour le client si param de config et type BL
        """
        res = super(StockPicking, self).do_transfer()
        if len(self) == 1 and res and self.user_has_groups('stock.group_production_lot') and \
                self.picking_type_id.code == 'outgoing' and\
                self.env['ir.values'].get_default('stock.config.settings', 'of_parc_installe_auto'):
            lots = self.pack_operation_product_ids.mapped('pack_lot_ids').mapped('lot_id')
            if lots:
                lots.sudo().creer_parc_installe(self)
        return res


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    of_parc_installe_id = fields.Many2one('of.parc.installe', string=u"Parc installé")

    @api.multi
    def creer_parc_installe(self, picking):
        u"""
        Appelée au moment de valider un BL pour créer automatiquement un parc installé au client
        :param picking: BL validé
        """
        parc_installe_obj = self.env['of.parc.installe']
        partner = picking.partner_id
        if not partner:
            return
        for lot in self:
            product = lot.product_id
            parc_installe_obj.create({
                'name': "%s - %s" % (lot.name, partner.name),
                'client_id': partner.id,
                'site_adresse_id': partner.id,
                'product_id': product.id,
                'brand_id': product.brand_id.id,
                'product_category_id': product.categ_id.id,
                'date_installation': fields.Date.today(),
                'date_service': picking.sale_id and fields.Date.to_string(
                    fields.Date.from_string(picking.sale_id.confirmation_date)),
                'lot_id': lot.id
            })


class StockSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    of_parc_installe_auto = fields.Boolean(
        string=u"(OF) Création automatique du parc installé",
        help=u"Créer automatiquement le parc installé lors de la confirmation du BL si un numéro de série est renseigné.")

    @api.multi
    def set_of_parc_installe_auto_defaults(self):
        if not bool(self.group_stock_production_lot):
            return self.env['ir.values'].sudo().set_default('stock.config.settings', 'of_parc_installe_auto', False)
        else:
            return self.env['ir.values'].sudo().set_default('stock.config.settings', 'of_parc_installe_auto',
                                                            self.of_parc_installe_auto)
