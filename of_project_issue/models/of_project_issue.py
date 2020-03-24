# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression
import time
import base64
from odoo.exceptions import UserError


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
    def default_get(self, fields=None):
        res = super(ProjectIssue, self).default_get(fields)
        res['date'] = lambda *a: time.strftime('%Y-%m-%d %H:%M:00')
        return res

    of_code = fields.Char('Code', size=64, required=True, readonly=True, default='Nouveau')
    partner_note = fields.Text("Note client", related='partner_id.comment', readonly=False)
    invoice_ids = fields.One2many('account.invoice', compute='_compute_invoice_ids', string='Factures du client', method=True, readonly=True)
    of_categorie_id = fields.Many2one('of.project.issue.categorie', u'Catégorie', required=False, ondelete='restrict')
    of_categorie_mere_id = fields.Many2one(related="of_categorie_id.pparent_id", string=u'Catégorie mère', store=True)
    of_canal_id = fields.Many2one('of.project.issue.canal', u'Canal', required=False, ondelete='restrict')
    of_garantie = fields.Boolean('Garantie', default=False)
    of_payant_client = fields.Boolean('Payant client', default=False)
    of_payant_fournisseur = fields.Boolean('Payant fournisseur', default=False)
    of_intervention = fields.Text("Nature de l'intervention")
    of_piece_commande = fields.Text(u'Pièces à commander')
    doc_ids = fields.One2many('of.sav.docs', 'project_issue_id', string="Liste de documents")
    fourn_ids = fields.One2many('res.partner', compute='_compute_fourn_ids', string="Fournisseurs", readonly=True, domain=[('supplier', '=', True)])
    fourn_msg_ids = fields.One2many('mail.message', compute='_compute_fourn_msg_ids', string="Historique fournisseur")
    interventions_liees = fields.One2many('of.planning.intervention', 'sav_id', u'RDVs Tech liés', readonly=False)
    of_partner_id_ref = fields.Char(u'Réf. contact', related='partner_id.ref', readonly=True)
    of_partner_id_address = fields.Char('Adresse', related='partner_id.contact_address', readonly=True)
    of_partner_id_phone = fields.Char(u'Téléphone', related='partner_id.phone', readonly=True)
    of_partner_id_mobile = fields.Char(u'Mobile', related='partner_id.mobile', readonly=True)
    of_partner_id_function = fields.Char(u'Fonction', related='partner_id.function', readonly=True)

    # @api.depends

    @api.depends
    def _compute_invoice_ids(self):
        invoice_obj = self.env['account.invoice']
        tre = {}
        for h in self:
            if h.partner_id:
                tre[h.id] = invoice_obj.search([('partner_id', '=', h.partner_id.id)])
            else:
                tre[h.id] = []
        return tre

    @api.depends
    def _compute_fourn_ids(self):
        fourns = {}
        for sav in self:
            f_ids = []
            for doc in sav.doc_ids:
                partner = doc.partner_id
                if partner and partner.supplier and partner.id not in f_ids:
                    f_ids.append(partner.id)
            fourns[sav.id] = f_ids
        return fourns

    @api.depends
    def _compute_fourn_msg_ids(self):
        mail_obj = self.env['mail.message']
        result = {}
        models = [('purchase.order', 'name'), ('account.invoice', 'internal_number')]

        for sav in self.read(['of_code']):
            of_codes = [sav['of_code']]

            mails = mail_obj.search(
                [('model', '=', self._name), ('res_id', '=', sav['id']), ('partner_id.supplier', '=', True)])
            model_ids = {model: [] for model, _ in models}

            while of_codes:
                of_code = of_codes.pop()
                for model, of_code_field in models:
                    mod_ids = self.pool[model].search([('partner_id.supplier', '=', True), ('origin', 'like', of_code),
                                                       ('id', 'not in', model_ids[model])])
                    if mod_ids:
                        model_ids[model] += mod_ids
                        mails += mail_obj.search([('model', '=', model), ('res_id', 'in', mod_ids)])
                        vals = self.pool[model].read(mod_ids, [of_code_field])
                        of_codes += [v[of_code_field] for v in vals]
            # On remet les mails dans l'ordre
            if mails:
                mails = mail_obj.search([('id', 'in', mails)])
            result[sav['id']] = mails
        return result

    # @api.onchange

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # Pour actualiser l'adresse et la liste des documents liés au partenaire
        super(ProjectIssue, self)._onchange_partner_id()
        docs = [(5,)]
        for i in self.liste_docs_partner():  # On récupère la liste des documents liés au partenaire (factures, ...)
            docs.append((0, 0, i))
        self.doc_ids = docs

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
    def action_creer_rdv(self):
        res = {
            'name': 'Rendez-vous',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.planning.intervention',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        if 'active_ids' in self._context.keys():
            active_ids = isinstance(self._context['active_ids'], (int, long)) and [self._context['active_ids']] or \
                         self._context['active_ids']
            if active_ids:
                project_issue = self.browse(active_ids[0])
                res['context'] = {'default_sav_id': project_issue.id}
                if project_issue.partner_id:
                    res['context']['default_partner_id'] = project_issue.partner_id.id
        return res

    @api.model
    def open_purchase_order(self):
        res = {
            'name': 'Demande de prix',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        if 'active_ids' in self._context.keys():
            active_ids = isinstance(self._context['active_ids'], (int, long)) and [self._context['active_ids']] or \
                         self._context['active_ids']
            if active_ids:
                project_issue = self.browse(active_ids[0])
                if project_issue.partner_id:
                    res['context'] = {'client_id': project_issue.partner_id.id,
                                      'default_origin': project_issue.of_code}
                else:
                    res['context'] = {'default_origin': project_issue.of_code}
        return res

    @api.model
    def open_sale_order(self):
        res = {
            'name': 'Devis',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        if 'active_ids' in self._context.keys():
            active_ids = isinstance(self._context['active_ids'], (int, long)) and [self._context['active_ids']] or \
                         self._context['active_ids']
            if active_ids:
                project_issue = self.browse(active_ids[0])
                if project_issue.partner_id:
                    res['context'] = {'default_partner_id': project_issue.partner_id.id,
                                      'default_origin': project_issue.of_code}
                else:
                    res['context'] = {'default_origin': project_issue.of_code}
        return res

    @api.multi
    def remind_user(self, attach=False, destination=True):
        # Appelée par bouton "Envoyer un rappel" courriel client
        for case in self:
            if not destination and not case.email_from:
                raise UserError("Erreur ! (#SAV105)\n\nL'adresse courriel SAV du client n'est pas renseignée.")
            if not case.user_id.user_email:
                raise UserError("Erreur ! (#SAV110)\n\nL'adresse courriel du responsable n'est pas renseignée.")
            if destination:
                case_email = self.env.user.user_email
                if not case_email:
                    case_email = case.user_id.user_email
            else:
                case_email = case.user_id.user_email
            src = case_email
            dest = case.user_id.user_email or ""
            body = case.description or ""
            for message in case.message_ids:
                if message.email_from and message.body_text:
                    body = message.body_text
                    break

            if not destination:
                src, dest = dest, case.email_from
                if body and case.user_id.signature:
                    if body:
                        body += '\n\n%s' % (case.user_id.signature)
                    else:
                        body = '\n\n%s' % (case.user_id.signature)

            body = self.format_body(body)

            attach_to_send = {}

            if attach:
                attach_ids = self.env['ir.attachment'].search(
                    [('res_model', '=', self._name), ('res_id', '=', case.id)])
                attach_to_send = self.env['ir.attachment'].read(attach_ids, ['datas_fname', 'datas'])
                attach_to_send = dict(
                    map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send))

            # Send an email
            subject = "Rappel SAV [%s] %s" % (case.of_code, case.name)

        return {
            'name': "Courriel SAV",
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'of.project.issue.mail.wizard',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'src': src,
                'dest': dest,
                'subject': subject,
                'body': body,
                'model': self._name,
                'reply_to': case.section_id.reply_to,
                'res_id': case.id,
                'attachments': attach_to_send,
                'context': self._context
            }
        }

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
            # Migration purchase_order_ids = self.env['purchase.order'].search(cr, uid, [('client_id', '=', partner_id)])
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

        docs.sort(key=lambda k: k['date'], reverse=True)  # Trie des résultats en fonction de la date
        return docs

    @api.model
    def remind_partner(self, attach=False):
        # Appelée par bouton "Envoyer un rappel" courriel responsable
        return self.remind_user(attach, destination=False)


class OfProjectIssueCategorie(models.Model):
    _name = "of.project.issue.categorie"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

    name = fields.Char(u'Catégorie', size=32)
    parent_id = fields.Many2one('of.project.issue.categorie', string=u'Catégorie parente', ondelete='restrict')
    pparent_id = fields.Many2one('of.project.issue.categorie', string=u'Catégorie mère', readonly=True)
    sequence = fields.Integer(u'Séquence', help=u"Ordre d'affichage (plus petit en premier)")
    parent_left = fields.Integer('Left Parent')
    parent_right = fields.Integer('Right Parent')

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

                categs = self.search([('parent_left', '>=', categ.parent_left), ('parent_left', '<', categ.parent_right)])
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

    name = fields.Char(u'Catégorie', size=32)


class OFSAVDocs(models.TransientModel):
    _name = 'of.sav.docs'
    _description = 'Liste des documents'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        # On détourne la fonction search pour peupler la liste de documents (onglet infos supplémentaires) à l'amorce de l'affichage de la vue
        res = super(OFSAVDocs, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
        if args and len(args) == 1 and len(args[0]) == 3 and args[0][0] == "project_issue_id":
            # Si la liste des docs a été mise à jour il y a moins de 15 s, c'est un appel répétitif, on ne génère pas une nouvelle liste
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

    name = fields.Char('Type du document', size=16)
    doc_objet = fields.Char('Objet du document', size=32)
    date = fields.Date('Date')
    number = fields.Char(u'Numéro', size=64)
    partner_id = fields.Many2one('res.partner', 'Partner')
    user_id = fields.Many2one('res.users', 'Responsable')
    date_due = fields.Date(u"Date d'échéance")
    origin = fields.Char("Document d'origine", size=64)
    residual = fields.Float('Balance', digits=(16, 2))
    amount_untaxed = fields.Float('HT', digits=(16, 2))
    amount_total = fields.Float('Total', digits=(16, 2))
    state = fields.Char(u'État', size=64)
    project_issue_id = fields.Many2one('project.issue', 'SAV')
    invoice_id = fields.Many2one('account.invoice', 'Facture')
    sale_order_id = fields.Many2one('sale.order', 'Devis/Commande Client')
    purchase_order_id = fields.Many2one('purchase.order', 'Commande Fournisseur')

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

    project_issue_ids = fields.One2many('project.issue', compute='_compute_project_issue_ids', string='SAV')

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
        'project.issue', string='SAV', readonly=False,
        domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")


class OfMailTemplate(models.Model):
    _inherit = "of.mail.template"

    @api.model
    def _get_allowed_models(self):
        return super(OfMailTemplate, self)._get_allowed_models() + ['project.issue']
