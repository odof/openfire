# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.of_geolocalize.models.of_geo import GEO_PRECISION


class OFParcInstalle(models.Model):
    _name = 'of.parc.installe'
    _description = u"Parc installé"

    name = fields.Char(string=u"No de série", size=64, required=False, copy=False)
    date_service = fields.Date(string=u"Date vente", required=False)
    date_installation = fields.Date(string=u"Date d'installation", required=False)
    date_fin_garantie = fields.Date(string=u"Fin de garantie")
    type_garantie = fields.Selection(selection=[
        ('initial', u"Initiale"),
        ('extension', u"Extension"),
        ('expired', u"Expirée")], string=u"Type de garantie")
    product_id = fields.Many2one(comodel_name='product.product', string=u"Produit", required=True, ondelete='restrict')
    product_category_id = fields.Many2one(comodel_name='product.category', string=u"Catégorie")
    client_id = fields.Many2one(
        comodel_name='res.partner', string=u"Client", required=True, domain="[('parent_id','=',False)]",
        ondelete='restrict')
    client_name = fields.Char(related='client_id.name')  # for map view
    client_mobile = fields.Char(related='client_id.mobile')  # for map view
    site_adresse_id = fields.Many2one(
        comodel_name='res.partner', string=u"Site installation", required=False,
        domain="['|',('parent_id','=',client_id),('id','=',client_id)]", ondelete='restrict')
    revendeur_id = fields.Many2one(
        comodel_name='res.partner', string=u"Revendeur", required=False, ondelete='restrict')
    installateur_id = fields.Many2one(
        comodel_name='res.partner', string=u"Installateur", required=False, ondelete='restrict')
    installateur_adresse_id = fields.Many2one(
        comodel_name='res.partner', string=u"Adresse installateur", required=False,
        domain="['|',('parent_id','=',installateur_id),('id','=',installateur_id)]", ondelete='restrict')
    note = fields.Text(string="Note")
    tel_site_id = fields.Char(string=u"Téléphone site installation", related='site_adresse_id.phone', readonly=True)
    street_site_id = fields.Char(string=u"Adresse", related='site_adresse_id.street', readonly=True)
    street2_site_id = fields.Char(string=u"Complément adresse", related='site_adresse_id.street2', readonly=True)
    zip_site_id = fields.Char(string=u"Code postal", related='site_adresse_id.zip', readonly=True, store=True)
    city_site_id = fields.Char(string=u"Ville", related='site_adresse_id.city', readonly=True)
    country_site_id = fields.Many2one(
        comodel_name='res.country', string=u"Pays", related='site_adresse_id.country_id', readonly=True)
    no_piece = fields.Char(string=u"N° pièce", size=64, required=False)
    project_issue_ids = fields.One2many(
        comodel_name='project.issue', inverse_name='of_produit_installe_id', string=u"SAV")
    active = fields.Boolean(string=u"Actif", default=True)
    brand_id = fields.Many2one(comodel_name='of.product.brand', string=u"Marque")
    modele = fields.Char(string=u"Modèle")
    installation = fields.Char(string=u"Type d'installation")
    conforme = fields.Boolean(string=u"Conforme", default=True)
    state = fields.Selection(
        selection=[
            ('neuf', "Neuf"),
            ('bon', "Bon"),
            ('usage', u"Usagé"),
            ('remplacer', u"À remplacer"),
        ], string=u"État", default="neuf")
    sale_order_ids = fields.Many2many(comodel_name='sale.order', string=u"Commandes")
    sale_order_amount = fields.Float(compute='_compute_links')
    account_invoice_ids = fields.Many2many(comodel_name='account.invoice', string=u"Factures")
    account_invoice_amount = fields.Float(compute='_compute_links')

    # Champs ajoutés pour la vue map
    geo_lat = fields.Float(string="geo_lat", compute='_compute_geo', store=True)
    geo_lng = fields.Float(string="geo_lng", compute='_compute_geo', store=True)
    precision = fields.Selection(
        GEO_PRECISION, default='not_tried', string="precision", compute='_compute_geo', store=True,
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string="Lot d'origine")

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

    @api.onchange('date_fin_garantie')
    def onchange_date_fin_garantie(self):
        if self.date_fin_garantie and self.date_fin_garantie < fields.Date.today():
            self.type_garantie = 'expired'
        elif self.date_fin_garantie and self.date_fin_garantie >= fields.Date.today() and \
                self.type_garantie == 'expired':
            self.type_garantie = 'extension'

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
            non_installateurs = self.mapped('installateur_id').filtered(lambda p: not p.of_installateur)
            non_installateurs.write({'of_installateur': True})
        return res

    @api.multi
    def name_get(self):
        """
        Permet dans un SAV lors de la saisie du no de série d'une machine installée de proposer les machines
        du contact précédées d'une puce.
        Permet dans une DI de proposer les appareils d'une adresse différente entre parenthèses.
        """
        if self._context.get('simple_display'):
            return super(OFParcInstalle, self).name_get()
        result = []
        client_id = self._context.get('partner_id_no_serie_puce')
        if client_id:
            for record in self:
                result.append((
                    record.id,
                    ("-> " if record.client_id.id == client_id else "")
                    + (record.name or u"(N° non renseigné)")
                    + " - " + record.client_id.display_name))
            return result

        for record in self:
            serial_number = '%s - ' % record.name if record.name else ''
            product_name = record.product_id.name
            partner_name = record.client_id.display_name
            record_name = '%s%s - %s' % (
                serial_number,
                product_name,
                partner_name,
            )
            result.append((record.id, record_name))
        return result

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

    # Autres

    @api.model
    def recompute_type_garantie_daily(self):
        today = fields.Date.today()
        all_parc_date_garantie = self.search([('date_fin_garantie', '!=', False)])
        # initialiser l'état de garantie pour les parcs qui ont une date de garantie future
        parc_garantie = all_parc_date_garantie.filtered(lambda p: p.date_fin_garantie >= today and not p.type_garantie)
        parc_garantie.write({'type_garantie': 'initial'})
        # Passer l'état de garantie à "Expirée" pour les parcs dont la date de garantie est future
        parc_expire = all_parc_date_garantie.filtered(
            lambda p: p.date_fin_garantie < today and p.type_garantie != 'expired')
        parc_expire.write({'type_garantie': 'expired'})
