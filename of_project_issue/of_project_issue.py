# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# MG from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
import time
import base64
import copy


class project_issue(osv.Model):
    """ Helpdesk Cases """
    
    _description = "Helpdesk"
    _inherit = 'project.issue'
    _rec_name = 'of_code'
    
    # le champ Etat, remplacer par les valeurs traduites
# MG
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

    def _of_set_code(self, cr, uid):
        """ Fonction lancee a l'installation, apres la creation de la sequence.
            Remplit la colonne 'of_code' pour tous les SAV deja saisis
        """
        to_set_of_code = self.search(cr, SUPERUSER_ID, [('of_code', '=', False)])
        if to_set_of_code:
            seq_obj = self.pool['ir.sequence']
            query = "UPDATE project_issue SET of_code='%s' WHERE id=%s"
            for helpdesk_id in to_set_of_code [::-1]:
                of_code = seq_obj.get(cr, SUPERUSER_ID, 'of.project.issue')
                if not of_code:
                    # La séquence n'a pas été trouvée
                    break
                cr.execute(query % (of_code, helpdesk_id))

    def _get_partner_invoices(self, cr, uid, ids, *args):
        invoice_obj = self.pool['account.invoice']
        tre = {}
        for h in self.browse(cr, uid, ids):
            if h.partner_id:
                tre[h.id] = invoice_obj.search(cr, uid, [('partner_id', '=', h.partner_id.id)])
            else:
                tre[h.id] = []
        return tre
    
    def _get_fournisseurs(self, cr, uid, ids, *args):
        fourns = {}
        for sav in self.browse(cr, uid, ids):
            f_ids = []
            for doc in sav.doc_ids:
                partner = doc.partner_id
                if partner and partner.supplier and partner.id not in f_ids:
                    f_ids.append(partner.id)
            fourns[sav.id] = f_ids
        return fourns

    def _get_fourn_messages(self, cr, uid, ids, *args):
        mail_obj = self.pool['mail.message']
        result = {}
        models = [('purchase.order','name'), ('account.invoice','internal_number')]

        for sav in self.read(cr, uid, ids, ['of_code']):
            of_codes = [sav['of_code']]

            mails = mail_obj.search(cr, uid, [('model','=',self._name),('res_id','=',sav['id']),('partner_id.supplier','=',True)])
            model_ids = {model:[] for model,_ in models}

            while of_codes:
                of_code = of_codes.pop()
                for model,of_code_field in models:
                    mod_ids = self.pool[model].search(cr, uid, [('partner_id.supplier','=',True),('origin','like',of_code),('id','not in',model_ids[model])])
                    if mod_ids:
                        model_ids[model] += mod_ids
                        mails += mail_obj.search(cr, uid, [('model','=',model),('res_id','in',mod_ids)])
                        vals = self.pool[model].read(cr, uid, mod_ids, [of_code_field])
                        of_codes += [v[of_code_field] for v in vals]
            # On remet les mails dans l'ordre
            if mails:
                mails = mail_obj.search(cr, uid, [('id','in',mails)])
            result[sav['id']] = mails
        return result

    def _get_show_partner_shop(self, cr, uid, ids, name, arg, context):
        res = {}
        for helpdesk in self.browse(cr, uid, ids, context=context):
            res[helpdesk.id] = helpdesk.shop_id.id != helpdesk.partner_shop_id.id
        return res

    def _get_categ_parent_id(self, cr, uid, ids, *args):
        result = {}
        for sav in self.browse(cr, uid, ids):
            if sav.categ_id:
                if sav.categ_id.parent_id:
                    categ_id = sav.categ_id.parent_id.id
                else:
                    categ_id = sav.categ_id.id
            else:
                categ_id = False
            result[sav.id] = categ_id
        return result

    def _get_categ_sav_ids(self, cr, uid, ids, context=None):
        return self.pool['of.project.issue'].search(cr, uid, [('categ_id','in',ids)])

    _columns = {
        'of_code'               : fields.char('Code', size=64, required=True, readonly=True, select=True), # Migration 9 states={'draft': [('readonly', False)]}, 
        'partner_note'          : fields.related('partner_id', 'comment', string="Note client", type='text', readonly=False),
        'invoice_ids'           : fields.function(_get_partner_invoices, string='Factures du client', method=True, type="one2many", obj='account.invoice', readonly=True),
        'of_categorie_id'       : fields.many2one('of.project.issue.categorie', u'Catégorie', required=False, ondelete='restrict'),
        'of_canal_id'           : fields.many2one('of.project.issue.canal', u'Canal', required=False, ondelete='restrict'),
        'of_garantie'           : fields.boolean('Garantie'),
        'of_payant_client'      : fields.boolean('Payant client'),
        'of_payant_fournisseur' : fields.boolean('Payant fournisseur'),
        'of_intervention'       : fields.text('Nature de l\'intervention'),
        'of_piece_commande'     : fields.text('Pièces à commander'),
        # MG 'shop_id'            : fields.many2one('sale.shop', 'Magasin'),
        # MG 'partner_shop_id'    : fields.related('partner_id','partner_maga', type="many2one", relation="sale.shop", string="Magasin client", readonly=True),
        'doc_ids'            : fields.one2many('of.sav.docs', 'project_issue_id', string="Liste de documents"),
        'doc_ids_dis'        : fields.related('doc_ids', type='one2many', relation='of.sav.docs', string="Liste de documents"),
        'fourn_ids'          : fields.function(_get_fournisseurs, string="Fournisseurs", type='one2many', obj='res.partner', readonly=True, domain=[('supplier','=',True)]),
        'fourn_msg_ids'      : fields.function(_get_fourn_messages, string="Historique fournisseur", type='one2many', obj='mail.message'),
        #Migration 9         'categ_parent_id'    : fields.function(_get_categ_parent_id, method=True, string=u"Catégorie parent", type='many2one', relation='crm.case.categ',
        #                                     store={'project.issue': (lambda self, cr, uid, ids, *a:ids, ['categ_id'], 10),
        #                                            'categ_id'    : (lambda self, cr, uid, ids, *a:self.pool['of.project.issue'].search(cr, uid, [('categ_id','in',ids)]), ['parent_id'], 10),
        #                                            }),
        # MG 'interventions_liees': fields.one2many('of.planning.pose', 'sav_id', 'Poses liees', readonly=False),
        # MG 'show_partner_shop'  : fields.function(_get_show_partner_shop, type="boolean", string="Magasin différent"),
    }

    _defaults = {
        'date'              : lambda *a: time.strftime('%Y-%m-%d %H:%M:00'),
        'of_garantie'          : False,
        'of_payant_client'     : False,
        'of_payant_fournisseur': False,
        'of_code'              : lambda self, cr, uid, context: self.pool['ir.sequence'].get(cr, uid, 'of.project.issue'),
        # MG 'show_partner_shop' : False,
    }
    
    _order = "date desc"

    # Quand on clique sur le bouton "Ouvrir" dans la liste des SAV pour aller sur le SAV
    def button_open_of_sav(self, cr, uid, ids, *args):
        sav_id = isinstance(ids, (int, long)) and ids or ids[0]
        if sav_id:           
            return {
                'name': 'SAV',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'project.issue',
                'res_id': sav_id,
                'type': 'ir.actions.act_window',
            }
    
    
    
#     def on_change_project(self, cr, uid, ids, project_id, context=None):
#          if project_id:
#              project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
#              if project and project.partner_id:
#                  return {'value': {'partner_id': project.partner_id.id}}
#          return {'value': {'partner_id': False}}
#     
    
    # Migration ok
    def onchange_shop_id(self, cr, uid, ids, shop_id, partner_shop_id):
        return {'value': {'show_partner_shop': shop_id != partner_shop_id}}

    # Migration ok
    def liste_docs_partner(self, cr, uid, partner_id=False):
        """ Renvoie la liste des documents (devis/commande, facture, commande fournisseur) liés à un partenaire
        Fonction appelée par onchange_partner_id et search de of_sav_docs"""
        docs = []
        invoice_obj = self.pool['account.invoice']
        sale_order_obj = self.pool['sale.order']
        purchase_order_obj = self.pool['purchase.order']
        state_inv_dict = {
            'draft': 'Brouillon',
            'proforma': 'Pro-forma',
            'proforma2': 'Pro-forma',
            'open': 'Ouverte',
            'paid': u'Pay\u00E9',
            'cancel': u'Annul\u00E9e'}
        state_sorder_dict = {
            'draft': 'Devis',
            'waiting_date': 'Attente de planification',
            'manual': u'\u00C0 facturer',
            'progress': 'En cours',
            'shipping_except': "Exception d'envoi",
            'invoice_except': 'Incident de facturation',
            'done': u'Termin\u00E9',
            'cancel': u'Annul\u00E9e',
            'sent': u'Envoyé'}
        state_porder_dict = {
            'draft': 'Demandes de prix',
            'wait': 'En attente',
            'confirmed': "En attente d'approbation",
            'approved': u'Confirm\u00E9 par fournisseur',
            'except_picking': "Exception d'envoi",
            'except_invoice': 'Incident de facturation',
            'done': u'Termin\u00E9',
            'cancel': u'Annul\u00E9e'}
        
        if partner_id:
            invoice_ids = invoice_obj.search(cr, uid, [('partner_id', '=', partner_id)])
            sale_order_ids = sale_order_obj.search(cr, uid, [('partner_id', '=', partner_id)])
            # Migration achats fournisseurs inhibés provisoirement car of_appro pas encore migré
            # Migration purchase_order_ids = purchase_order_obj.search(cr, uid, [('client_id', '=', partner_id)])
            if invoice_ids:
                for inv in invoice_obj.browse(cr, uid, invoice_ids):
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
                        'state': inv.state, # M9 state_inv_dict[inv.state],
                        'invoice_id': inv.id,
                    })
            if sale_order_ids:
                for s_order in sale_order_obj.browse(cr, uid, sale_order_ids):
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
                        'state': s_order.state, # M9 state_sorder_dict[s_order.state],
                        'sale_order_id': s_order.id,
                    })
            # Migration achats fournisseurs inhibés provisoirement car of_appro pas encore migré
#             if purchase_order_ids:
#                 for p_order in purchase_order_obj.browse(cr, uid, purchase_order_ids):
#                     docs.append({
#                         'name': 'Commande Fournisseur',
#                         'doc_objet': 'purchase.order',
#                         'date': p_order.date_order or False,
#                         'number': p_order.name or '',
#                         'partner_id': p_order.partner_id.id,
#                         'user_id': p_order.validator and p_order.validator.id or False,
#                         'date_due': p_order.date_approve or False,
#                         'origin': p_order.origin or '',
#                         'amount_untaxed': p_order.amount_untaxed or 0,
#                         'amount_total': p_order.amount_total or 0,
#                         'state': p_order.state, # M9 state_porder_dict[p_order.state],
#                         'purchase_order_id': p_order.id,
#                     })
        docs.sort(key=lambda k: k['date'], reverse=True) # Trie des résultats en fonction de la date
        return docs

    
    def on_change_project(self, cr, uid, ids, project_id, context=None):
        # Le on_change_project de project.issue remet à False le partner_id, ce qui pose problème quand on veut créer un SAV depuis une action (ex: créer un SAV depuis le parc installé pour Win...).
        # Le champ partner_id n'est pas propagé puisqu'il est remis à False si on utilise pas les projets ce qui est notre cas.
        # On remet le partner_id si la variable default_partner_id est définie et si partner_id est à False
        
        res = super(project_issue, self).on_change_project(cr, uid, ids, project_id, context=context)
        if context and not res['value']['partner_id'] and context.get('default_partner_id', False):
            res['value']['partner_id'] = context.get('default_partner_id', False)
        return res
    
    # Migration ok
    def on_change_partner_id(self, cr, uid, ids, partner_id):
        # Pour actualiser la liste des documents liés à au partenaire
        res = super(project_issue, self).onchange_partner_id(cr, uid, ids, partner_id)
        docs = [[5, ]]
        for i in self.liste_docs_partner(cr, uid, partner_id): # On récupère la liste des documents liés au partenaire (factures, ...)
            docs.append([0, 0, i])
        
        if res and res.has_key('value'):
            res['value'].update({'doc_ids': docs, 'doc_ids_dis': docs})
        else:
            res = {'value':{'doc_ids': docs, 'doc_ids_dis': docs}}
# Migration of_magasin pas encore migré
#         if partner_id:
#             partner = self.pool['res.partner'].browse(cr, uid, partner_id)
#             partner_maga_id = partner.partner_maga and partner.partner_maga.id or False
#             res['value'].update({
#                 'shop_id'          : partner_maga_id,
#                 'partner_shop_id'  : partner_maga_id,
#                 'show_partner_shop': False,
#             })
        return res

    # Migration ok
    def open_purchase_order(self, cr, uid, context={}):
        if not context:
            context = {}
        res = {
            'name': 'Demande de prix',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        if 'active_ids' in context.keys():
            active_ids = isinstance(context['active_ids'], (int,long)) and [context['active_ids']] or context['active_ids']
            if active_ids:
                project_issue = self.browse(cr, uid, active_ids[0])
                if project_issue.partner_id:
                    res['context'] = {'client_id'     : project_issue.partner_id.id,
                                      'default_origin': project_issue.of_code}
                else:
                    res['context'] = {'default_origin': project_issue.of_code}
        return res

    # Migration ok
    def open_sale_order(self, cr, uid, context={}):
        if not context:
            context = {}
        res = {
            'name': 'Devis',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        if 'active_ids' in context.keys():
            active_ids = isinstance(context['active_ids'], (int,long)) and [context['active_ids']] or context['active_ids']
            if active_ids:
                project_issue = self.browse(cr, uid, active_ids[0])
                if project_issue.partner_id:
                    res['context'] = {'default_partner_id': project_issue.partner_id.id,
                                      'default_origin'    : project_issue.of_code}
                else:
                    res['context'] = {'default_origin': project_issue.of_code}
        return res

    def copy(self, cr, uid, helpdesk_id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'of_code': self.pool['ir.sequence'].get(cr, uid, 'of.project.issue'),
        })
        return super(project_issue, self).copy(cr, uid, helpdesk_id, default, context=context)
    
    def remind_partner(self, cr, uid, ids, context=None, attach=False):
        # Appelée par bouton "Envoyer un rappel" courriel responsable
        return self.remind_user(cr, uid, ids, context, attach, destination=False)

    def remind_user(self, cr, uid, ids, context=None, attach=False, destination=True):
        # Appelée par bouton "Envoyer un rappel" courriel client
        for case in self.browse(cr, uid, ids, context=context):
            if not destination and not case.email_from:
                raise osv.except_osv(('Erreur ! (#SAV105)'), "L'adresse courriel SAV du client n'est pas renseignée.")
            if not case.user_id.user_email:
                raise osv.except_osv(('Erreur ! (#SAV110)'), "L'adresse courriel du responsable n'est pas renseignée.")
            if destination:
                case_email = self.pool['res.users'].browse(cr, uid, uid, context=context).user_email
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
                attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', case.id)])
                attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname', 'datas'])
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
                'context': context                
            }
        }
    
# MG
# class of_project_issue_mail_wizard(osv.TransientModel):
#     """
#     Interface envoi rappel courriel depuis SAV
#     """
#     _name = 'of.project.issue.mail.wizard'
#     _description = "Interface envoi rappel courriel depuis SAV"
#     
#     _columns={
#         'src': fields.char('De', size=128, required=True),
#         'dest': fields.char('À', size=128, required=True),
#         'subject': fields.text('Sujet', required=True),
#         'body': fields.text('Contenu', required=True),
#         'model': fields.char('Model', size=64, required=False),
#         'reply_to': fields.char('Répondre à', size=128, required=False),
#         'res_id': fields.integer("res_id"),
#         'context': fields.text('Contexte', required=False)
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
#         reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
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
#         'complete_name': fields.function(_name_get_fnc, type="char", string='Catégorie'),
#         'parent_id': fields.many2one('crm.case.categ', u'Cat\u00E9gorie parent', select=True, ondelete='cascade'),
#         'child_id': fields.one2many('crm.case.categ', 'parent_id', string=u'Cat\u00E9gories enfants'),
#         'parent_left': fields.integer('Parent gauche', select=1),
#         'parent_right': fields.integer(u'Parent droit', select=1),
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
#         for categ in self.read(cr, uid, ids, ['parent_left','parent_right'], context=context):
#             domain += ['&',('parent_left','>=',categ['parent_left']),('parent_right','<=',categ['parent_right'])]
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
class of_project_issue_categorie(osv.Model):
    _name = "of.project.issue.categorie"
    
    _columns = {
        'name': fields.char(u'Catégorie', size=32),
    }

# Canal SAV
class of_project_issue_canal(osv.Model):
    _name = "of.project.issue.canal"
    
    _columns = {
        'name': fields.char(u'Catégorie', size=32),
    }
   

# Migration ok
class of_sav_docs(osv.TransientModel):
    
    _name = 'of.sav.docs'
    _description = 'Liste des documents'
    
    _columns = {
        'name': fields.char('Type du document', size=16),
        'doc_objet': fields.char('Objet du document', size=32),
        'date': fields.date('Date'),
        'number': fields.char(u'Num\u00E9ro', size=64),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'user_id': fields.many2one('res.users', 'Responsable'),
        'date_due': fields.date(u'Date d\'\u00E9ch\u00E9ance'),
        'origin': fields.char('Document d\'origine', size=64),
        'residual': fields.float('Balance', digits=(16, 2)),
        'amount_untaxed': fields.float('HT', digits=(16, 2)),
        'amount_total': fields.float('Total', digits=(16, 2)),
        'state': fields.char('Etat', size=64),
        'project_issue_id': fields.many2one('project.issue', 'SAV'),
        'invoice_id': fields.many2one('account.invoice', 'Facture'),
        'sale_order_id': fields.many2one('sale.order', 'Devis/Commande Client'),
        'purchase_order_id': fields.many2one('purchase.order', 'Commande Fournisseur'),
    }
    
    # Migration ok
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # On détourne la fonction search pour peupler la liste de documents (onglet infos supplémentaires) à l'amorce de l'affichage de la vue
        res = super(of_sav_docs, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order, context=context, count=count)
        if args and len(args) == 1 and len(args[0]) == 3 and args[0][0] == "project_issue_id":
            # Si la liste des docs a été mise à jour il y a moins de 15 s, c'est un appel répétitif, on ne génère pas une nouvelle liste
            if res:
                cr.execute("Select (extract(epoch from now() at time zone 'UTC') - extract(epoch from create_date)) FROM of_sav_docs WHERE id = %s limit 1", (res[0],))
                b = cr.fetchone()[0]
                if b < 15:
                    return res

            # On extrait l'id du SAV dans la requête du search
            if isinstance(args[0][2], list):
                sav_id = args[0][2][0]
            else:
                sav_id = args[0][2]             
            # On supprime les enregistrements existants
            if sav_id:
                if res:
                    self.unlink(cr, uid, res, context=context)
            obj_sav = self.pool['project.issue']
            sav = obj_sav.browse(cr, uid, sav_id)
            if sav.partner_id:
                # On récupère la liste des documents liés au partenaire (factures, ...)
                res = []
                for i in obj_sav.liste_docs_partner(cr, uid, sav.partner_id.id):
                    i.update({'project_issue_id': sav_id})
                    res.append(self.create(cr, uid, i, context=context)) 
        return res

    # Migration ok
    # Quand on clique sur le bouton "Ouvrir" de la liste des documents dans la vue SAV
    def button_open_of_sav(self, cr, uid, ids, *args):
        if ids:
            doc = self.browse(cr, uid, isinstance(ids, (int,long)) and ids or ids[0])
            res_model = doc.doc_objet
            if res_model == 'account.invoice':
                name = 'Factures Clients'
                res_id = doc.invoice_id.id
            elif res_model == 'sale.order':
                name = 'Devis / Commandes Clients'
                res_id = doc.sale_order_id.id
            elif res_model == 'purchase.order':
                name = 'Demande de prix / Commandes Fournisseurs'
                res_id = doc.purchase_order_id.id

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
class res_partner(osv.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
     
    _columns = {
           'project_issue_ids': fields.one2many('project.issue', 'partner_id', 'SAV'),
       }
    
# Migration
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
#         'courriels': fields.function(_get_courriels, string="Courriels", type='char', size=256),
#     }

# Migration
# class of_planning_pose(osv.Model):
#     _name = "of.planning.pose"
#     _inherit = "of.planning.pose"
#  
#     _columns = {
#         'sav_id': fields.many2one('project.issue', 'SAV', readonly=False),
#     }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

