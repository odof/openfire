# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression
import time
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProjectIssue(models.Model):
    """ Helpdesk Cases """
    _description = "Helpdesk"
    _inherit = 'project.issue'
    _order = "date desc"
    _rec_name = 'of_code'

    # Init

    @api.model
    def _of_set_code(self):
        """ Fonction lancée à l'installation, après la création de la séquence.
            Remplit la colonne 'of_code' pour tous les SAV déjà saisis
        """
        to_set_of_code = self.sudo().search(['|', ('of_code', '=', ''), ('of_code', '=', False)])
        if to_set_of_code:
            seq_obj = self.env['ir.sequence']
            query = "UPDATE project_issue SET of_code='%s' WHERE id=%s"
            for helpdesk_id in to_set_of_code[::-1]:
                of_code = seq_obj.sudo().get('of.project.issue')
                if not of_code:
                    # La séquence n'a pas été trouvée
                    break
                self._cr.execute(query % (of_code, helpdesk_id.id))

    # Default

    @api.model
    def default_get(self, fields_list):
        res = super(ProjectIssue, self).default_get(fields_list)
        res['date'] = time.strftime('%Y-%m-%d %H:%M:00')

        return res

    # @api.model
    # def _default_company(self):
    #     if self.env['ir.values'].get_default('of.intervention.settings', 'company_choice') == 'user':
    #         return self.env['res.company']._company_default_get('project.issue')
    #     return False

    # Modification du default défini dans project.issue
    # company_id = fields.Many2one(default=lambda s: s._default_company())
    of_code = fields.Char("Code", required=True, readonly=True, default='Nouveau')
    partner_note = fields.Text("Note client", related='partner_id.comment', readonly=False)
    invoice_ids = fields.One2many('account.invoice', compute='_get_partner_invoices', string="Factures du client")
    saleorder_ids = fields.One2many('sale.order', compute='_compute_saleorder_ids', string="Commandes client")
    purchaseorder_ids = fields.One2many(
        'purchase.order', compute='_compute_purchaseorder_ids', string="Commandes fournisseur")
    saleorder_count = fields.Integer("Nombre de commande (client)", compute='_compute_saleorder_ids')
    purchaseorder_count = fields.Integer("Nombre de commande (fournisseur)", compute='_compute_purchaseorder_ids')
    of_categorie_id = fields.Many2one('of.project.issue.categorie', string=u"Catégorie", ondelete='restrict')
    of_categorie_mere_id = fields.Many2one(related='of_categorie_id.pparent_id', string=u"Catégorie mère", store=True)
    of_canal_id = fields.Many2one('of.project.issue.canal', string=u"Canal", required=False, ondelete='restrict')
    of_garantie = fields.Boolean("Garantie")
    of_payant_client = fields.Boolean("Payant client")
    of_payant_fournisseur = fields.Boolean("Payant fournisseur")
    of_intervention = fields.Text("Nature de l'intervention")
    of_piece_commande = fields.Text(u'Pièces à commander')
    doc_ids = fields.One2many('of.sav.docs', 'project_issue_id', string="Liste de documents")
    interventions_liees = fields.One2many('of.planning.intervention', 'sav_id', string=u"Interventions liées")
    interventions_count = fields.Integer(string="Nombre d'intervention", compute='_compute_interventions_count')
    of_partner_id_ref = fields.Char(u"Réf. contact", related='partner_id.ref', readonly=True)
    of_partner_id_address = fields.Char("Adresse", related='partner_id.contact_address', readonly=True)
    of_partner_id_phone = fields.Char(u"Téléphone", related='partner_id.phone', readonly=True)
    of_partner_id_mobile = fields.Char(u"Mobile", related='partner_id.mobile', readonly=True)
    of_partner_id_function = fields.Char(u"Fonction", related='partner_id.function', readonly=True)
    # active_test indispensable car il y a un active_test à False sur of_user_profile_id dans of_access_control
    of_create_uid_profile_id = fields.Many2one(
        related="create_uid.of_user_profile_id", string=u"Profil de création",
        readonly=True, context={'active_test': True})

    company_id = fields.Many2one(default=False)

    of_create_date_formatted = fields.Char(
        string=u"Date de création formatée", compute='_compute_of_create_date_formatted')
    of_planification_date = fields.Datetime(string=u"Date de planification", compute='_compute_of_planification_date')
    of_line_ids = fields.One2many(comodel_name='of.project.issue.line', inverse_name='issue_id', string="Facturation")
    of_sale_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Position fiscale (client)",
        domain="[('tax_ids.tax_src_id.type_tax_use','=','sale')]"
    )
    of_purchase_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Position fiscale (fournisseur)",
        help="La position fiscale par défaut qui sera renseignée si le fournisseur de \
        l'article n'a pas lui même de position fiscale."
    )

    # @api.depends

    @api.depends("of_datetime_prise_charge", "of_datetime_resolution")
    def _compute_delai(self):
        for sav in self:
            if sav.of_datetime_prise_charge:
                datetime_start = datetime.strptime(sav.create_date, "%Y-%m-%d %H:%M:%S")
                datetime_stop = datetime.strptime(sav.of_datetime_prise_charge, "%Y-%m-%d %H:%M:%S")
                delta = datetime_stop - datetime_start
                sav.of_delai_prise_charge = float((delta.days * 24) + (delta.seconds / 3600))
            if sav.of_datetime_resolution and sav.of_datetime_prise_charge:
                datetime_start = datetime.strptime(sav.of_datetime_prise_charge, "%Y-%m-%d %H:%M:%S")
                datetime_stop = datetime.strptime(sav.of_datetime_resolution, "%Y-%m-%d %H:%M:%S")
                delta = datetime_stop - datetime_start
                sav.of_delai_resolution = float((delta.days * 24) + (delta.seconds / 3600))

    @api.depends("of_code")
    def _compute_saleorder_ids(self):
        saleorder_obj = self.env['sale.order']
        for sav in self:
            saleorder_ids = saleorder_obj.search([('origin', '=', sav.of_code)])
            sav.saleorder_ids = saleorder_ids
            sav.saleorder_count = len(saleorder_ids)

    @api.depends("of_code")
    def _compute_purchaseorder_ids(self):
        purchaseorder_obj = self.env['purchase.order']
        for sav in self:
            purchaseorder_ids = purchaseorder_obj.search([('origin', '=', sav.of_code)])
            sav.purchaseorder_ids = purchaseorder_ids
            sav.purchaseorder_count = len(purchaseorder_ids)

    @api.depends("interventions_liees")
    def _compute_interventions_count(self):
        for sav in self:
            sav.interventions_count = len(sav.interventions_liees)

    @api.depends
    def _get_partner_invoices(self):
        invoice_obj = self.env['account.invoice']
        tre = {}
        for h in self:
            if h.partner_id:
                tre[h.id] = invoice_obj.search([('partner_id', '=', h.partner_id.id)])
            else:
                tre[h.id] = []
        return tre

    @api.depends('create_date')
    def _compute_of_create_date_formatted(self):
        for rec in self:
            rec.of_create_date_formatted = datetime.strptime(rec.create_date, DEFAULT_SERVER_DATETIME_FORMAT). \
                strftime('%d/%m/%Y') if rec.create_date else None

    @api.depends('interventions_liees', 'interventions_liees.date')
    def _compute_of_planification_date(self):
        for rec in self:
            if rec.interventions_liees:
                rdvs = rec.interventions_liees.filtered(lambda rdv: rdv.date > fields.Datetime.now())
                if rdvs:
                    rec.of_planification_date = rdvs[0].date
                else:
                    rec.of_planification_date = rec.interventions_liees[-1].date

    # @api.onchange

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # Pour actualiser l'adresse et la liste des documents liés au partenaire
        super(ProjectIssue, self)._onchange_partner_id()
        docs = [(5,)]
        for i in self.liste_docs_partner():  # On récupère la liste des documents liés au partenaire (factures, ...)
            docs.append((0, 0, i))
        self.doc_ids = docs
        if self.partner_id:
            # Pour les objets du planning, le choix de la société se fait par un paramètre de config
            company_choice = self.env['ir.values'].get_default(
                'of.intervention.settings', 'company_choice') or 'contact'
            if company_choice == 'contact' and self.partner_id.company_id:
                self.company_id = self.partner_id.company_id.id

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if not self.project_id:
            partner_id = self.partner_id
            email_from = self.email_from
            super(ProjectIssue, self)._onchange_project_id()
            self.partner_id = partner_id
            self.email_from = email_from
        else:
            super(ProjectIssue, self)._onchange_project_id()

    # Héritages

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """
        Surcharge de la fonction pour afficher toutes les étapes existantes sur vue kanban
        """
        search_domain = ['|', ('project_ids', '=', False), ('id', 'in', stages.ids)]
        # retrieve project_id from the context, add them to already fetched columns (ids)
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain
        # perform search
        return stages.search(search_domain, order=order)

    @api.model
    def create(self, vals):
        if vals.get('of_code', 'Nouveau') == 'Nouveau':
            vals['of_code'] = self.env['ir.sequence'].next_by_code('of.project.issue') or 'New'
        return super(ProjectIssue, self).create(vals)

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if not default:
            default = {}
        default.update({
            'of_code': self.env['ir.sequence'].get('of.project.issue'),
        })
        return super(ProjectIssue, self).copy(default)

    # Actions

    # Quand on clique sur le bouton "Ouvrir" dans la liste des SAV pour aller sur le SAV

    @api.multi
    def button_open_of_sav(self):
        if self.ensure_one():
            return {
                'name': 'SAV',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'project.issue',
                'res_id': self._ids[0],
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_saleorder(self):
        if self.ensure_one():
            return {
                'name': 'Commandes client',
                'view_mode': 'tree,kanban,form',
                'res_model': 'sale.order',
                'res_id': self.saleorder_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.saleorder_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_purchaseorder(self):
        if self.ensure_one():
            return {
                'name': 'Commandes fournisseur',
                'view_mode': 'tree,kanban,form',
                'res_model': 'purchase.order',
                'res_id': self.purchaseorder_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.purchaseorder_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_intervention(self):
        if self.ensure_one():
            return {
                'name': 'Interventions',
                'view_mode': 'tree,kanban,form',
                'res_model': 'of.planning.intervention',
                'res_id': self.interventions_liees.ids,
                'domain': "[('id', 'in', %s)]" % self.interventions_liees.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_creer_rdv(self):
        res = {
            'name': 'Rendez-vous',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.planning.intervention',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        active_ids = self._context.get('active_ids')
        if active_ids:
            project_issue = self.browse(active_ids[0])
            res['context'] = {'default_sav_id': project_issue.id}
            if project_issue.partner_id:
                res['context']['default_address_id'] = project_issue.partner_id.id
        return res

    @api.model
    def open_purchase_order(self):
        self.ensure_one()
        res = {
            'name': 'Demande de prix',
            'view_mode': 'form,tree',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        if not self.of_line_ids:
            if self.partner_id:
                res['context'] = {'client_id': self.partner_id.id,
                                  'default_origin': self.of_code}
            else:
                res['context'] = {'default_origin': self.of_code}
        else:
            purchase_obj = self.env['purchase.order']
            lines_by_supplier = {}
            no_supplier = []
            # Séparer les ligne par fournisseur, lignes sans fournisseur ignorées pour l'instant
            for line in self.of_line_ids:
                suppliers = line.product_id.seller_ids \
                                .filtered(lambda r: (not r.company_id or r.company_id == line.company_id) and
                                                    (not r.product_id or r.product_id == line.product_id))
                if suppliers:
                    supplier = suppliers[0].name  # supplier.name est un many2one vers res.partner
                    if supplier not in lines_by_supplier:
                        lines_by_supplier[supplier] = []
                    lines_by_supplier[supplier].append(line)
                else:
                    no_supplier.append(line)
            purchase_orders = purchase_obj
            # Création de chaque CF
            for supplier, lines in lines_by_supplier.iteritems():
                # utilisation de new() pour trigger les onchanges facilement
                purchase_order_new = purchase_obj.new({
                    'partner_id': supplier.id,
                    'customer_id': self.partner_id.id,
                    'origin': self.of_code,
                })
                purchase_order_new.onchange_partner_id()
                order_values = purchase_order_new._convert_to_write(purchase_order_new._cache)
                # On passe la position fiscale ici car si un onchange_partner_id() est appelé, il la supprime
                if not order_values.get("fiscal_position_id", False):
                    order_values["fiscal_position_id"] = self.of_purchase_fiscal_position_id \
                                                         and self.of_purchase_fiscal_position_id.id
                purchase_order = purchase_obj.create(order_values)
                purchase_lines = []
                for line in lines:
                    line_vals = line._prepare_purchase_order_line(purchase_order)
                    purchase_lines.append((0, 0, line_vals))
                purchase_order.write({'order_line': purchase_lines})
                purchase_orders |= purchase_order
            # Si plusieurs CF retourner vue liste avec les différentes CF
            # Si une seule, afficher la CF en vue form
            if len(purchase_orders) > 1:
                res['view_mode'] = 'tree,kanban,form'
                res['domain'] = "[('id', 'in', %s)]" % purchase_orders.ids
            elif len(purchase_orders) == 1:
                res['res_id'] = purchase_orders.id
        return res

    @api.model
    def open_sale_order(self):
        self.ensure_one()
        res = {
            'name': 'Devis',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
            }
        if not self.of_line_ids or not self.of_sale_fiscal_position_id:
            if self.partner_id:
                res['context'] = {'default_partner_id': self.partner_id.id,
                                  'default_origin': self.of_code}
            else:
                res['context'] = {'default_origin': self.of_code}
        else:
            sale_obj = self.env['sale.order']
            # utilisation de new() pour trigger les onchanges facilement
            sale_order_new = sale_obj.new({
                'partner_id': self.partner_id.id,
                'origin': self.of_code,
            })
            sale_order_new.onchange_partner_id()
            sale_order_new.update({'fiscal_position_id': self.of_sale_fiscal_position_id.id})
            order_values = sale_order_new._convert_to_write(sale_order_new._cache)
            sale_order = sale_obj.create(order_values)
            lines_to_create = []
            # Récupération des lignes de commandes
            for line in self.of_line_ids:
                line_vals = line._prepare_sale_order_line(sale_order)
                lines_to_create.append((0, 0, line_vals))
            sale_order.write({'order_line': lines_to_create})
            # Renvoyer la commande créée
            res['res_id'] = sale_order.id

        return res

    # Autres

    @api.multi
    def liste_docs_partner(self):
        """ Renvoie la liste des documents (devis/commande, facture, commande fournisseur) liés à un partenaire
        Fonction appelée par onchange_partner_id et search de of_sav_docs"""
        self.ensure_one()
        partner_id = self.partner_id.id
        docs = []

        if partner_id:
            invoice_ids = self.env['account.invoice'].search([('partner_id', '=', partner_id)])
            sale_order_ids = self.env['sale.order'].search([('partner_id', '=', partner_id)])
            # Migration achats fournisseurs inhibés provisoirement car of_appro pas encore migré
            # Migration purchase_order_ids = self.env['purchase.order']
            # .search(cr, uid, [('client_id', '=', partner_id)])
            if invoice_ids:
                for inv in invoice_ids:
                    docs.append({
                        'name': 'Facture',
                        'doc_objet': 'account.invoice',
                        'date': inv.date_invoice or False,
                        'number': inv.number or '',
                        'partner_id': partner_id,
                        'user_id': inv.user_id and inv.user_id.id or False,
                        'date_due': inv.date_due or False,
                        'origin': inv.origin or '',
                        'residual': inv.residual or 0,
                        'amount_untaxed': inv.amount_untaxed or 0,
                        'amount_total': inv.amount_total or 0,
                        'state': inv.state,
                        'invoice_id': inv.id,
                    })
            if sale_order_ids:
                for s_order in sale_order_ids:
                    docs.append({
                        'name': 'Devis/Commande client',
                        'doc_objet': 'sale.order',
                        'date': s_order.date_order or False,
                        'number': s_order.name or '',
                        'partner_id': partner_id,
                        'user_id': s_order.user_id and s_order.user_id.id or False,
                        'date_due': s_order.validity_date or False,
                        'origin': s_order.origin or '',
                        'amount_untaxed': s_order.amount_untaxed or 0,
                        'amount_total': s_order.amount_total or 0,
                        'state': s_order.state,
                        'sale_order_id': s_order.id,
                    })

        # Tri des résultats en fonction de la date
        docs.sort(key=lambda k: k['date'], reverse=True)
        return docs


class OfProjectIssueCategorie(models.Model):
    _name = "of.project.issue.categorie"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

    name = fields.Char(u"Catégorie")
    parent_id = fields.Many2one('of.project.issue.categorie', string=u"Catégorie parente", ondelete='restrict')
    pparent_id = fields.Many2one('of.project.issue.categorie', string=u"Catégorie mère", readonly=True)
    sequence = fields.Integer(u"Séquence", help=u"Ordre d'affichage (plus petit en premier)")
    parent_left = fields.Integer("Left Parent")
    parent_right = fields.Integer("Right Parent")

    _constraints = [
        (models.Model._check_recursion, 'Error ! You can not create recursive category.', ['parent_id'])
    ]

    _defaults = {
        'sequence': 10
    }

    # Héritages

    # Pour afficher la hiérarchie des catégories
    @api.multi
    def name_get(self):
        if not self._ids:
            return []
        res = []
        for record in self:
            name = [record.name]
            parent = record.parent_id
            while parent:
                name.append(parent.name)
                parent = parent.parent_id
            name = ' / '.join(name[::-1])
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Pour inclure la recherche sur le nom des parents"""
        args = list(args or [])
        negation = operator in expression.NEGATIVE_TERM_OPERATORS
        if negation:
            operator = expression.TERM_OPERATORS_NEGATION[operator]
        if not (name == '' and operator == 'ilike'):
            args += [(self._rec_name, operator, name)]
        categs = self.search(args)
        categs = categs._get_children()
        if negation:
            categs = self.search([('id', 'not in', categs._ids)], limit=limit)
        else:
            categs = categs[:limit]
        res = categs.name_get()
        return res

    @api.model
    def create(self, vals):
        res = super(OfProjectIssueCategorie, self).create(vals)
        res.pparent_id = res.parent_id and res.parent_id.pparent_id or res
        return res

    @api.multi
    def write(self, vals):
        res = super(OfProjectIssueCategorie, self).write(vals)

        if 'parent_id' in vals:
            for categ in self:
                parent = categ
                while parent.parent_id:
                    parent = parent.parent_id

                categs = self.search([('parent_left', '>=', categ.parent_left),
                                      ('parent_left', '<', categ.parent_right)])
                categs.write({'pparent_id': parent.id})
        return res

    # Autres

    @api.multi
    def _get_children(self):
        """ Retourne la liste des ids ainsi que leurs enfants et petits-enfants en respectant self._order"""
        domain = ['|' for _ in xrange(len(self.ids) - 1)]
        for categ in self.read(['parent_left', 'parent_right']):
            domain += ['&', ('parent_left', '>=', categ['parent_left']), ('parent_right', '<=', categ['parent_right'])]
        return self.search(domain)


class OFProjectIssuerCanal(models.Model):
    _name = "of.project.issue.canal"

    name = fields.Char(u'Catégorie')


class OFSAVDocs(models.TransientModel):
    _name = 'of.sav.docs'
    _description = 'Liste des documents'

    name = fields.Char("Type du document")
    doc_objet = fields.Char("Objet du document")
    date = fields.Date("Date")
    number = fields.Char(u"Numéro")
    partner_id = fields.Many2one('res.partner', string="Partenaire")
    user_id = fields.Many2one('res.users', string="Responsable")
    date_due = fields.Date(u"Date d'échéance")
    origin = fields.Char("Document d'origine")
    residual = fields.Float("Balance", digits=(16, 2))
    amount_untaxed = fields.Float("HT", digits=(16, 2))
    amount_total = fields.Float("Total", digits=(16, 2))
    state = fields.Char(u"État")
    project_issue_id = fields.Many2one('project.issue', string="SAV")
    invoice_id = fields.Many2one('account.invoice', string="Facture")
    sale_order_id = fields.Many2one('sale.order', string="Devis/Commande Client")
    purchase_order_id = fields.Many2one('purchase.order', string="Commande Fournisseur")

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        # On détourne la fonction search pour peupler la liste de documents (onglet infos supplémentaires)
        #  à l'amorce de l'affichage de la vue
        res = super(OFSAVDocs, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
        if args and len(args) == 1 and len(args[0]) == 3 and args[0][0] == "project_issue_id":
            # Si la liste des docs a été mise à jour il y a moins de 15 sec, c'est un appel répétitif,
            #  on ne génère pas une nouvelle liste
            if res:
                self._cr.execute(
                    "SELECT (extract(epoch from now() at time zone 'UTC') - extract(epoch from create_date)) "
                    "FROM of_sav_docs WHERE id = %s limit 1", (res[0].id,))
                if self._cr.fetchone()[0] < 15:
                    return res

            # On extrait l'id du SAV dans la requête du search
            if isinstance(args[0][2], list):
                sav_id = args[0][2][0]
            else:
                sav_id = args[0][2]
            # On supprime les enregistrements existants
            if sav_id:
                if res:
                    res.unlink()
            obj_sav = self.env['project.issue']
            sav = obj_sav.browse(sav_id)
            if sav.partner_id:
                # On récupère la liste des documents liés au partenaire (factures, ...)
                res_ids = []
                for i in sav.liste_docs_partner():
                    i.update({'project_issue_id': sav_id})
                    res_ids.append(self.create(i).id)
                res = self.browse(res_ids)
        return res

    # Quand on clique sur le bouton "Ouvrir" de la liste des documents dans la vue SAV
    @api.multi
    def button_open_of_sav(self):
        if self._ids:
            res_model = self.doc_objet
            if res_model == 'account.invoice':
                name = 'Factures Clients'
                res_id = self.invoice_id.id
            elif res_model == 'sale.order':
                name = 'Devis / Commandes Clients'
                res_id = self.sale_order_id.id
            elif res_model == 'purchase.order':
                name = 'Demande de prix / Commandes Fournisseurs'
                res_id = self.purchase_order_id.id

            return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': res_model,
                'res_id': res_id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    project_issue_ids = fields.One2many('project.issue', compute='_compute_project_issue_ids', string="SAV")

    @api.multi
    @api.depends('child_ids.project_issue_ids')
    def _compute_project_issue_ids(self):
        """Pour afficher les SAV de tous les enfants du partenaire dans l'historique"""
        issue_obj = self.env['project.issue']
        for partner in self:
            partners = [partner]

            ind = 0
            while ind < len(partners):
                partners += partners[ind].child_ids
                ind += 1
            partner_ids = [p.id for p in partners]
            partner.project_issue_ids = issue_obj.search([('partner_id', 'in', partner_ids)])


class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _inherit = "of.planning.intervention"

    sav_id = fields.Many2one(
        'project.issue', string="SAV", domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")
    sav_of_code = fields.Char(string="SAV Code", related='sav_id.of_code')
    saleorder_ids = fields.One2many(
        'sale.order', related='sav_id.saleorder_ids', string="Commandes client", readonly=True)
    purchaseorder_ids = fields.One2many(
        'purchase.order', related='sav_id.purchaseorder_ids', string="Commandes fournisseur", readonly=True)
    saleorder_count = fields.Integer(
        string="Nombre de commandes (client)", related='sav_id.saleorder_count', readonly=True)
    purchaseorder_count = fields.Integer(
        string="Nombre de commandes (fournisseur)", related='sav_id.purchaseorder_count', readonly=True)

    @api.multi
    def action_view_saleorder(self):
        self.ensure_one()
        return self.sav_id and self.sav_id.action_view_saleorder()

    @api.multi
    def action_view_purchaseorder(self):
        self.ensure_one()
        return self.sav_id and self.sav_id.action_view_purchaseorder()

    @api.multi
    def action_view_sav(self):
        if self.ensure_one():
            return {
                'name': 'SAV',
                'view_mode': 'form,tree,kanban',
                'res_model': 'project.issue',
                'res_id': self.sav_id.id,
                'domain': "[('id', '=', %s)]" % self.sav_id.id,
                'type': 'ir.actions.act_window',
            }


class OfMailTemplate(models.Model):
    _inherit = "of.mail.template"

    @api.model
    def _get_allowed_models(self):
        return super(OfMailTemplate, self)._get_allowed_models() + ['project.issue']


class OfProjectIssueLine(models.Model):
    _name = 'of.project.issue.line'
    _description = "Helpdesk Line"

    issue_id = fields.Many2one(comodel_name='project.issue', string="SAV", required=True)
    product_id = fields.Many2one(comodel_name='product.product', string="Article", required=True)
    qty = fields.Float(string=u"Qté", required=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", related='issue_id.company_id')

    @api.multi
    def _prepare_sale_order_line(self, order):
        sale_line_obj = self.env['sale.order.line']
        order_line_new = sale_line_obj.new({
            'product_id': self.product_id.id,
            'order_id': order.id
            })
        order_line_new.product_id_change()
        order_line_new.product_uom_change()
        order_line_new.update({'product_uom_qty': self.qty})
        return order_line_new._convert_to_write(order_line_new._cache)

    @api.multi
    def _prepare_purchase_order_line(self, order):
        purchase_line_obj = self.env['purchase.order.line']
        order_line_new = purchase_line_obj.new({
            'product_id': self.product_id.id,
            'order_id': order.id
            })
        order_line_new.onchange_product_id()
        order_line_new.update({'product_qty': self.qty})
        order_line_new._onchange_quantity()
        return order_line_new._convert_to_write(order_line_new._cache)
