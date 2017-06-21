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
    _rec_name = 'of_code'

    # le champ Etat, remplacer par les valeurs traduites
# Migration
#     def _of_finish_install(self, cr, uid):
#         cr.execute("SELECT * FROM information_schema.columns WHERE table_name='of_sav_docs' AND column_name='state'")
#         if cr.fetchone():
#             cr.execute("UPDATE of_sav_docs SET state = 'Brouillon' WHERE state = 'Draft' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'Ouverte' WHERE state = 'Open' ");
#             cr.execute(u"UPDATE of_sav_docs SET state = 'Pay\u00E9' WHERE state = 'Paid' ");
#             cr.execute(u"UPDATE of_sav_docs SET state = 'Annul\u00E9e' WHERE state = 'Cancelled' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'Devis' WHERE state = 'Quotation' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'Attente de planification' WHERE state = 'Waiting Schedule' ");
#             cr.execute(u"UPDATE of_sav_docs SET state = '\u00C0 facturer' WHERE state = 'To Invoice' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'En cours' WHERE state = 'In Progress' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'Exception d''envoi' WHERE state = 'Shipping Exception' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'Incident de facturation' WHERE state = 'Invoice Exception' ");
#             cr.execute(u"UPDATE of_sav_docs SET state = 'Termin\u00E9' WHERE state = 'Done' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'Demandes de prix' WHERE state = 'Request for Quotation' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'En attente' WHERE state = 'Waiting' ");
#             cr.execute("UPDATE of_sav_docs SET state = 'En attente d''approbation' WHERE state = 'Waiting Approval' ");
#             cr.execute(u"UPDATE of_sav_docs SET state = 'Confirm\u00E9 par fournisseur' WHERE state = 'Approved' ");

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

    @api.depends
    def _get_fournisseurs(self):
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
    def _get_fourn_messages(self):
        mail_obj = self.env['mail.message']
        result = {}
        models = [('purchase.order', 'name'), ('account.invoice', 'internal_number')]

        for sav in self.read(['of_code']):
            of_codes = [sav['of_code']]

            mails = mail_obj.search([('model', '=', self._name), ('res_id', '=', sav['id']), ('partner_id.supplier', '=', True)])
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

        # Migration
        # @api.depends
        # def _get_show_partner_shop(self, name, arg, context):
        #     res = {}
        #     for helpdesk in self:
        #         res[helpdesk.id] = helpdesk.shop_id.id != helpdesk.partner_shop_id.id
        #     return res

        # Migration
        # def _get_categ_parent_id(self, cr, uid, ids, *args):
        #     result = {}
        #     for sav in self.browse(cr, uid, ids):
        #         if sav.categ_id:
        #             if sav.categ_id.parent_id:
        #                 categ_id = sav.categ_id.parent_id.id
        #             else:
        #                 categ_id = sav.categ_id.id
        #         else:
        #             categ_id = False
        #         result[sav.id] = categ_id
        #     return result

    of_code = fields.Char('Code', size=64, required=True, readonly=True, select=True, default='Nouveau')  # Migration 9 states={'draft': [('readonly', False)]},
    partner_note = fields.Text("Note client", related='partner_id.comment', readonly=False)
    invoice_ids = fields.One2many('account.invoice', compute='_get_partner_invoices', string='Factures du client', method=True, readonly=True)
    of_categorie_id = fields.Many2one('of.project.issue.categorie', u'Catégorie', required=False, ondelete='restrict')
    of_categorie_mere_id = fields.Many2one(related="of_categorie_id.pparent_id", string=u'Catégorie mère', store=True)
    of_canal_id = fields.Many2one('of.project.issue.canal', u'Canal', required=False, ondelete='restrict')
    of_garantie = fields.Boolean('Garantie', default=False)
    of_payant_client = fields.Boolean('Payant client', default=False)
    of_payant_fournisseur = fields.Boolean('Payant fournisseur', default=False)
    of_intervention = fields.Text("Nature de l'intervention")
    of_piece_commande = fields.Text('Pièces à commander')
    # Migration 'shop_id'            : fields_oldapi.many2one('sale.shop', 'Magasin'),
    # Migration 'partner_shop_id'    : fields_oldapi.related('partner_id', 'partner_maga', type="many2one", relation="sale.shop", string="Magasin client", readonly=True),
    doc_ids = fields.One2many('of.sav.docs', 'project_issue_id', string="Liste de documents")
    fourn_ids = fields.One2many('res.partner', compute='_get_fournisseurs', string="Fournisseurs", readonly=True, domain=[('supplier', '=', True)])
    fourn_msg_ids = fields.One2many('mail.message', compute='_get_fourn_messages', string="Historique fournisseur")
    # Migration 9        'categ_parent_id'    : fields_oldapi.function(_get_categ_parent_id, method=True, string=u"Catégorie parent", type='many2one', relation='crm.case.categ',
    #                                     store={'project.issue': (lambda self, cr, uid, ids, *a:ids, ['categ_id'], 10),
    #                                            'categ_id'    : (lambda self, cr, uid, ids, *a:self.pool['of.project.issue'].search(cr, uid, [('categ_id', 'in', ids)]), ['parent_id'], 10),
    #                                            }),
    interventions_liees = fields.One2many('of.planning.intervention', 'sav_id', u'Interventions liées', readonly=False)
    # Migration 'show_partner_shop'  : fields_oldapi.function(_get_show_partner_shop, type="boolean", string="Magasin différent"),
    of_partner_id_ref = fields.Char(u'Réf. contact', related='partner_id.ref', readonly=True)
    of_partner_id_address = fields.Char('Adresse', related='partner_id.contact_address', readonly=True)
    of_partner_id_phone = fields.Char(u'Téléphone', related='partner_id.phone', readonly=True)
    of_partner_id_mobile = fields.Char(u'Mobile', related='partner_id.mobile', readonly=True)
    of_partner_id_function = fields.Char(u'Fonction', related='partner_id.function', readonly=True)

    _defaults = {
        'date' : lambda *a: time.strftime('%Y-%m-%d %H:%M:00'),
        # Migration 'show_partner_shop' : False,
    }

    _order = "date desc"

    @api.onchange('project_id')
    def _on_change_project_id(self):
        if not self.project_id:
            partner_id = self.partner_id
            email_from = self.email_from
            super(ProjectIssue, self)._onchange_project_id()
            self.partner_id = partner_id
            self.email_from = email_from
        else:
            super(ProjectIssue, self)._onchange_project_id()

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

    # Migration magasin non migré
    # @api.onchange('shop_id')
    # def onchange_shop_id(self, shop_id, partner_shop_id):
    #     return {'value': {'show_partner_shop': shop_id != partner_shop_id}}

    # Migration ok
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
                        'name': 'Devis/Commande Client',
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
            # Migration achats fournisseurs inhibés provisoirement car of_appro pas encore migré
            # if purchase_order_ids:
            #     for p_order in self.env['purchase.order'].browse(cr, uid, purchase_order_ids):
            #         docs.append({
            #             'name': 'Commande Fournisseur',
            #             'doc_objet': 'purchase.order',
            #             'date': p_order.date_order or False,
            #             'number': p_order.name or '',
            #             'partner_id': p_order.partner_id.id,
            #             'user_id': p_order.validator and p_order.validator.id or False,
            #             'date_due': p_order.date_approve or False,
            #             'origin': p_order.origin or '',
            #             'amount_untaxed': p_order.amount_untaxed or 0,
            #             'amount_total': p_order.amount_total or 0,
            #             'state': p_order.state,
            #             'purchase_order_id': p_order.id,
            #         })
        docs.sort(key=lambda k: k['date'], reverse=True)  # Trie des résultats en fonction de la date
        return docs

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # Pour actualiser l'adresse et la liste des documents liés au partenaire
        super(ProjectIssue, self)._onchange_partner_id()
        docs = [(5, )]
        for i in self.liste_docs_partner():  # On récupère la liste des documents liés au partenaire (factures, ...)
            docs.append((0, 0, i))

        self.doc_ids = docs

        # Migration of_magasin pas encore migré
        #         if partner_id:
        #             partner = self.pool['res.partner'].browse(cr, uid, partner_id)
        #             partner_maga_id = partner.partner_maga and partner.partner_maga.id or False
        #             res['value'].update({
        #                 'shop_id'          : partner_maga_id,
        #                 'partner_shop_id'  : partner_maga_id,
        #                 'show_partner_shop': False,
        #             })

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
            active_ids = isinstance(self._context['active_ids'], (int, long)) and [self._context['active_ids']] or self._context['active_ids']
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
            active_ids = isinstance(self._context['active_ids'], (int, long)) and [self._context['active_ids']] or self._context['active_ids']
            if active_ids:
                project_issue = self.browse(active_ids[0])
                if project_issue.partner_id:
                    res['context'] = {'client_id'     : project_issue.partner_id.id,
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
            active_ids = isinstance(self._context['active_ids'], (int, long)) and [self._context['active_ids']] or self._context['active_ids']
            if active_ids:
                project_issue = self.browse(active_ids[0])
                if project_issue.partner_id:
                    res['context'] = {'default_partner_id': project_issue.partner_id.id,
                                      'default_origin'    : project_issue.of_code}
                else:
                    res['context'] = {'default_origin': project_issue.of_code}
        return res

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

    @api.model
    def remind_partner(self, attach=False):
        # Appelée par bouton "Envoyer un rappel" courriel responsable
        return self.remind_user(attach, destination=False)

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
                attach_ids = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', case.id)])
                attach_to_send = self.env['ir.attachment'].read(attach_ids, ['datas_fname', 'datas'])
                attach_to_send = dict(map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send))

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

# Migration
# class of_project_issue_mail_wizard(osv.TransientModel):
#     """
#     Interface envoi rappel courriel depuis SAV
#     """
#     _name = 'of.project.issue.mail.wizard'
#     _description = "Interface envoi rappel courriel depuis SAV"
#
#     _columns={
#         'src': fields_oldapi.char('De', size=128, required=True),
#         'dest': fields_oldapi.char('À', size=128, required=True),
#         'subject': fields_oldapi.text('Sujet', required=True),
#         'body': fields_oldapi.text('Contenu', required=True),
#         'model': fields_oldapi.char('Model', size=64, required=False),
#         'reply_to': fields_oldapi.char('Répondre à', size=128, required=False),
#         'res_id': fields_oldapi.integer("res_id"),
#         'context': fields_oldapi.text('Contexte', required=False)
#     }
#
#     def default_get(self, cr, uid, fields_list=None, context=None):
#         """ Remplie les champs de l'interface courriel avec les valeurs par défaut"""
#         if not context:
#             return False
#         result = {'src': context.get('src', []),
#                   'dest': context.get('dest', []),
#                   'subject': context.get('subject', []),
#                   'body': context.get('body', []),
#                   'model': context.get('model', []),
#                   'reply_to': context.get('reply_to', []),
#                   'res_id': context.get('res_id', []),
#                   }
#         result.update(super(of_project_issue_mail_wizard, self).default_get(cr, uid, fields_list, context=context))
#         return result
#
#     def envoyer_courriel(self, cr, uid, ids, context=None):
#         # On récupère les données du wizard
#         wizard = self.browse(cr, uid, ids[0], context=context)
#         src = wizard.src
#         dest = wizard.dest
#         subject = wizard.subject
#         body = wizard.body
#         model = wizard.model
#         reply_to = wizard.reply_to
#         res_id = wizard.res_id
#         attachments = {}
#
#         if not src or not dest or not subject or not body or not model or not res_id:
#             return False
#
#         body = self.pool['base.action.rule'].format_body(body)
#
#         mail_message = self.pool['mail.message']
#         mail_message.schedule_with_attach(cr, uid,
#             src,
#             [dest],
#             subject,
#             body,
#             model=model,
#             reply_to=reply_to,
#             res_id=res_id,
#             attachments=attachments,
#             context=context
#         )
#         return {'type': 'ir.actions.act_window_close'}

# Migration 9 plus crm_case_categ
# class crm_case_categ(osv.Model):
#     """ Category of Case """
#     _name = "crm.case.categ"
#     _inherit = "crm.case.categ"
#
#     # Migration ok
#     def name_get(self, cr, uid, ids, context=None):
#         if not len(ids):
#             return []
#         reads = self.read(cr, uid, ids, ['name', 'parent_id'], context=context)
#         res = []
#         for record in reads:
#             name = record['name']
#             if record['parent_id']:
#                 name = record['parent_id'][1]+' / '+name
#             res.append((record['id'], name))
#         return res
#
#     # Migration ok
#     def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
#         res = self.name_get(cr, uid, ids, context=context)
#         return dict(res)
#
#     _columns = {
#         'complete_name': fields_oldapi.function(_name_get_fnc, type="char", string='Catégorie'),
#         'parent_id': fields_oldapi.many2one('crm.case.categ', u'Cat\u00E9gorie parent', select=True, ondelete='cascade'),
#         'child_id': fields_oldapi.one2many('crm.case.categ', 'parent_id', string=u'Cat\u00E9gories enfants'),
#         'parent_left': fields_oldapi.integer('Parent gauche', select=1),
#         'parent_right': fields_oldapi.integer(u'Parent droit', select=1),
#     }
#
#     _constraints = [
#         (osv.Model._check_recursion, u'Erreur ! Vous ne pouvez pas cr\u00E9er de cat\u00E9gories r\u00E9cursives', ['parent_id'])
#     ]
#
#     _parent_name = "parent_id"
#     _parent_store = True
#     _parent_order = 'name'
#     _order = 'parent_left'
#
#     # Migration ok
#     def _get_children(self, cr, uid, ids, context=None):
#         """ Retourne la liste des ids ainsi que leurs enfants et petits-enfants en respectant self._order
#         """
#         domain = ['|' for _ in xrange(len(ids)-1)]
#         for categ in self.read(cr, uid, ids, ['parent_left', 'parent_right'], context=context):
#             domain += ['&',('parent_left', '>=',categ['parent_left']),('parent_right', '<=',categ['parent_right'])]
#         return self.search(cr, uid, domain, context=context)
#
#     # Migration ok
#     def _name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100, name_get_uid=None):
#         if args is None:
#             args = []
#         if context is None:
#             context = {}
#         args = args[:]
#         # optimize out the default criterion of ``ilike ''`` that matches everything
#         if not (name == '' and operator == 'ilike'):
#             args += [(self._rec_name, operator, name)]
#         access_rights_uid = name_get_uid or user
#         ids = self._search(cr, user, args, limit=limit, context=context, access_rights_uid=access_rights_uid)
#         ids = self._get_children(cr, user, ids, context=None)
#         res = self.name_get(cr, access_rights_uid, ids, context)
#         return res

# Catégorie de SAV
class OfProjectIssueCategorie(models.Model):
    _name = "of.project.issue.categorie"

    name = fields.Char(u'Catégorie', size=32)
    parent_id = fields.Many2one('of.project.issue.categorie', 'Catégorie parente', select=True, ondelete='restrict')
    pparent_id = fields.Many2one('of.project.issue.categorie', string='Catégorie mère', readonly=True)
    sequence = fields.Integer(u'Séquence', help=u"Ordre d'affichage (plus petit en premier)")
    parent_left = fields.Integer('Left Parent', select=1)
    parent_right = fields.Integer('Right Parent', select=1)

    _constraints = [
        (models.Model._check_recursion, 'Error ! You can not create recursive category.', ['parent_id'])
    ]

    _defaults = {
        'sequence' : 10
    }

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

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

    @api.multi
    def _get_children(self):
        """ Retourne la liste des ids ainsi que leurs enfants et petits-enfants en respectant self._order
        """
        domain = ['|' for _ in xrange(len(self.ids)-1)]
        for categ in self.read(['parent_left', 'parent_right']):
            domain += ['&', ('parent_left', '>=', categ['parent_left']), ('parent_right', '<=', categ['parent_right'])]
        return self.search(domain)

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

# Canal SAV
class of_project_issue_canal(models.Model):
    _name = "of.project.issue.canal"

    name = fields.Char(u'Catégorie', size=32)

class of_sav_docs(models.TransientModel):

    _name = 'of.sav.docs'
    _description = 'Liste des documents'

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
    state = fields.Char('État', size=64)
    project_issue_id = fields.Many2one('project.issue', 'SAV')
    invoice_id = fields.Many2one('account.invoice', 'Facture')
    sale_order_id = fields.Many2one('sale.order', 'Devis/Commande Client')
    purchase_order_id = fields.Many2one('purchase.order', 'Commande Fournisseur')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        # On détourne la fonction search pour peupler la liste de documents (onglet infos supplémentaires) à l'amorce de l'affichage de la vue
        res = super(of_sav_docs, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
        if args and len(args) == 1 and len(args[0]) == 3 and args[0][0] == "project_issue_id":
            # Si la liste des docs a été mise à jour il y a moins de 15 s, c'est un appel répétitif, on ne génère pas une nouvelle liste
            if res:
                self._cr.execute("SELECT (extract(epoch from now() at time zone 'UTC') - extract(epoch from create_date)) "
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

# Ajout historique SAV dans vue partenaires
class ResPartner(models.Model):
    _inherit = 'res.partner'

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

    project_issue_ids = fields.One2many('project.issue', compute='_compute_project_issue_ids', string='SAV')

# Migration
#     def _get_courriels(self, cr, uid, ids, *args):
#         result = {}
#         for part in self.browse(cr, uid, ids):
#             email = ''
#             if part.supplier:
#                 emails = []
#                 for adr in part.address:
#                     email = adr.email
#                     if email and email not in emails:
#                         emails.append(email)
#                 email = ' || '.join(emails)
#             result[part.id] = email
#         return result
#
#     _columns = {
#         'courriels': fields_oldapi.function(_get_courriels, string="Courriels", type='char', size=256),
#     }

class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _inherit = "of.planning.intervention"

    sav_id = fields.Many2one('project.issue', string='SAV', readonly=False)
