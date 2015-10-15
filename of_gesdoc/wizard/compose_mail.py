# -*- encoding: utf-8 -*-

import time
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
import pypdftk
import os
import base64

def get_id(cr, uid, id, champ=False, table=False):
    try:
        if table and champ:
            cr.execute("SELECT id from " + str(table) + " WHERE " + str(champ) + "='" + str(id) + "'")
            pre = cr.fetchone()[0]
        else: pre = ""
    except:
        pre = ""
    return pre

def get_ch(cr, uid, id, champ=False, table=False):
    try:
        if table and champ:
            cr.execute("SELECT " + str(champ) + " from " + str(table) + " WHERE id='" + str(id) + "'")
            pre = cr.fetchone()[0]
        else: pre = ""
    except:
        pre = ""
    return pre


class of_compose_mail(osv.AbstractModel):
    _name = 'of.compose.mail'
    _description = 'Courrier'

    _columns = {
        'name'          : fields.char('Sujet', size=64),
        'lettre_id'     : fields.many2one('of.mail.template', 'Modele'),
        'date_paie'     : fields.date('Date Paiement'),
        'amount_acompte': fields.float('Montant Acompte'),
        'content'       : fields.text('Contenu'),
        'file'          : fields.binary(u'Modèle PDF'),
        'file_name'     : fields.char('Nom du fichier', size=64),
        'res_file'      : fields.binary(u'Fichier complété', readonly=1),
        'res_file_name' : fields.char('Nom du fichier resultat', size=64),
        'file_url'      : fields.char('URL du fichier', size=64),
        'chp_tmp_ids'   : fields.one2many('of.gesdoc.chp.tmp', 'compose_id', 'Liste des champs'),
        'len_chp_tmp'   : fields.integer('Length'),
    }

    def format_body(self, cr, uid, body):
        return (body or u'').encode('utf8', 'ignore')

    def _get_objects(self, cr, uid, o, data, context):
        # La variable data pourra etre utilisee dans des fonctions heritees, notamment dans of_planning_res pour active_model et active_ids
        partner_obj = self.pool['res.partner']

        partner = o if o._name == 'res.partner' else o.partner_id
        order = False
        invoice = False

        if o._name == 'sale.order':
            order = o
            for line in o.order_line:
                if line.invoice_lines:
                    invoice = line.invoice_lines[0].invoice_id
                    break
        elif o._name == 'account.invoice':
            invoice = o
            for line in o.invoice_line_ids:
                if line.sale_line_ids:
                    order = line.sale_line_ids[0].order_id
                    break

        addresses = partner.address_get(adr_pref=['contact','delivery'])
        address = addresses['contact'] and partner_obj.browse(cr, uid, addresses['contact'])
        address_pose = addresses['delivery'] and partner_obj.browse(cr, uid, addresses['delivery'])

        result = {
            'address_pose': address_pose,
            'address'     : address,
            'partner'     : partner,
            'order'       : order,
            'invoice'     : invoice,
        }
        return result

    def _get_dict_values(self, cr, uid, data, obj, context):
        if not data['ids']:
            return {}
        if context is None:
            context = {}
        lang_obj = self.pool['res.lang']

        o = obj.browse(cr, uid, data['ids'][0])

        objects = self._get_objects(cr, uid, o, data, context)
        context['objects'] = objects # Mise a disposition des objets pour les modules herites
        order = objects.get('order',False)
        invoice = objects.get('invoice',False)
        partner = objects.get('partner',False)
        address = objects.get('address',False)
        address_pose = objects.get('address_pose',False)

        lang_code = context.get('lang', partner.lang)
        lang_id = lang_obj.search(cr, uid, [('code','=', lang_code)])[0]

        values = (
            ('amount_total', o, ''),
            ('origin', o, ''),
            ('date_order', order or o, ''),
            ('date_confirm', order or o, ''),
            ('date_invoice', invoice or o, ''),
            ('date_order', order, ''),
            ('residual', invoice or o, ''),
            ('number', invoice, ''),
            ('user_id', o, ''),
            ('objet', o, ''),
        )

        res = {key: getattr(obj, key, default) for key,obj,default in values}

        res['date_confirm_order'] = res['date_confirm']
        del res['date_confirm']
        res['user'] = res['user_id'] and res['user_id'].name
        del res['user_id']

        res.update({
            'c_title'           : address and address.title.name or 'Madame, Monsieur',
            'c_name'            : address and address.name or (address.partner_id and address.partner_id.name) or '',
            'c_street'          : address and address.street or '',
            'c_street2'         : address and address.street2 or '',
            'c_zip'             : address and address.zip or '',
            'c_city'            : address and address.city or '',
            'c_phone'           : address and address.phone or '',
            'c_mobile'          : address and address.mobile or '',
            'c_fax'             : address and address.fax or '',
            'c_email'           : address and address.email or '',
            'c_adr_pose_name'   : address_pose and address_pose.name or (address_pose.partner_id and address_pose.partner_id.name or '') or '',
            'c_adr_pose_street' : address_pose and address_pose.street or '',
            'c_adr_pose_street2': address_pose and address_pose.street2 or '',
            'c_adr_pose_city'   : address_pose and address_pose.city or '',
            'c_adr_pose_zip'    : address_pose and address_pose.zip or '',
            'date'              : time.strftime('%d/%m/%Y'),
            'date_paie'         : data['form'].get('date_paie',''),
            'amount_acompte'    : lang_obj.format(cr, uid, [lang_id], '%.2f', data['form'].get('amount_acompte',0), grouping=True)
        })

        lang = lang_obj.browse(cr, uid, lang_id)
        date_length = len((datetime.now()).strftime(DEFAULT_SERVER_DATE_FORMAT))
        for date_field in ('date_order', 'date_confirm_order', 'date_invoice', 'date_paie'):
            if not res[date_field]:
                continue
            # reformatage de la date (copie depuis report_sxw : rml_parse.formatLang())
            date = datetime.strptime(res[date_field][:date_length], DEFAULT_SERVER_DATE_FORMAT)
            date = date.strftime(lang.date_format.encode('utf-8'))
            res[date_field] = date
        return res

    def _format_lettre(self, cr, uid, data, content, obj, context=None):
        if context is None:
            # Definir le contexte des maintenant evitera de le verifier a chaque heritage de _get_dict_values
            # pour la transmission du context['objects']
            context = {}
        vals = self._get_dict_values(cr, uid, data, obj, context)

        # La fonction _get_dict_values ajoute une valeur 'objects' au contexte
        # Il faut supprimer ce contexte avant qu'il ne soit renvoye sans quoi l'encodeur json generera une erreur
        del context['objects']
        return self.format_body(cr, uid, content % vals)

    def get_lettre(self, cr, uid, ids, context={}):
        res = {}
        if context is None: context = {}
        lettre_obj = self.pool['of.mail.template']
        model_obj = self.pool['ir.model.data']
        tmp = self.read(cr, uid, ids, ['lettre_id', 'date_paie', 'amount_acompte'])
        data = {
            'ids' : context.get('active_ids', []),
            'model' : context.get('model', []),
            'form' : tmp and tmp[0] or {},
        }

        dataids = data['ids']
        context.update(data_ids = dataids)
        obj = self.pool[data['model']]

        #get information of mail's model when user chooses a model
        view_ref = 'view_courrier_wizard2'
        lettre_id = data['form'].get('lettre_id')
        if lettre_id:
            lettre = lettre_obj.browse(cr, uid, lettre_id[0])
            res = {
                'name': lettre.name,
                'date_paie': data['form']['date_paie'],
                'amount_acompte': data['form']['amount_acompte'],
            }

            if lettre.file:
                view_ref = 'view_courrier_wizard2_file'
                res['file'] = lettre.file
                res['file_name'] = lettre.file_name or ''
                res['file_url'] = lettre.file_url or ''
                res['chp_tmp_ids'] = []
                for chp in lettre.chp_ids:
                    res['chp_tmp_ids'].append((0, 0, {
                        'name': chp.name or '',
                        'value_openfire': chp.value_openfire and self._format_lettre(cr, uid, data, chp.value_openfire, obj) or '',
                    }))
                res['len_chp_tmp'] = lettre.len_chp or 0
            else:
                res['content'] = self._format_lettre(cr, uid, data, lettre.body_text, obj)

            self.write(cr, uid, ids, res)

        view = model_obj.get_object_reference(cr, uid, 'of_gesdoc', view_ref)

        return {
            'name': 'Envoyer un courrier',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view and [view[1]] or False,
            'res_model': 'of.compose.mail',
            'src_model': data['model'],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids and ids[0] or False,
            'context': context,
        }

    #print a mail in the format pdf
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        lettre_obj = self.pool['of.mail.template']
        users_obj = self.pool['res.users']
        tmp = self.read(cr, uid, ids)
        data = {
            'ids' : context.get('data_ids', []),
            'model' : context.get('model', []),
            'form' : tmp and tmp[0] or {},
        }
        lett_id = data['form']['lettre_id'][0]
        obj = self.pool[data['model']]
        for o in obj.browse(cr, uid, data['ids']):
            #information of customer
            partner = o if data['model'] == 'res.partner' else o.partner_id
            if partner.child_ids:
                partner = partner.child_ids[0]

            #Update partner comment
            let_obj = lettre_obj.browse(cr, uid, lett_id)
            text = time.strftime('%Y-%m-%d') + ": Envoi d'un courrier \"" + lettre_obj.name_get(cr,uid,lett_id)[0][1] + "\" (" + users_obj.name_get(cr,uid,uid)[0][1] + ")\n"

            comment = partner.comment or ''
            if comment and comment[-1] != '\n':
                comment += '\n' + text
            else:
                comment += text
            partner.write({'comment':comment})

        #test if user has checked 'sans adresse' and 'sans entete'
        #self._log_event(cr, uid, ids, data, context=context)
        if(data['model'] == 'res.partner'):
            if let_obj.sans_add:
                act = 'courriers_se'
            else:
                act = 'courriers'
        elif(data['model'] == 'sale.order'):
            if let_obj.sans_add: 
                act = 'courriers_sale_se'
            else: 
                act = 'courriers_sale'
        elif(data['model'] == 'crm.lead'):
            if let_obj.sans_add: 
                act = 'courriers_crm_se'
            else: 
                act = 'courriers_crm'
        elif(data['model'] == 'account.invoice'):
            if let_obj.sans_add: 
                act = 'courriers_account_se'
            else: 
                act = 'courriers_account'
        if let_obj.sans_header: 
            act += '_sehead'
        return {
            'type' : 'ir.actions.report.xml',
            'report_name':'of_gesdoc.' + act,
            'datas' : data,
        }

    def print_report_acrobat(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        model_obj = self.pool['ir.model.data']
        ids = isinstance(ids, long or int) and [ids] or ids
        mail_template_obj = self.pool['of.mail.template']
        if ids:
            datas = {}
            for chp in self.browse(cr, uid, ids[0]).chp_tmp_ids:
                datas[chp.name or ''] = chp.value_openfire or ''

            compose = self.browse(cr, uid, ids[0])
            file_url = compose.file_url

            # si le fichier pdf n'existe pas(ex: on fait la copie de la base), si le champ file existe, on recree le fichier dans le serveur
            if not os.path.isfile(file_url):
                if compose.file:
                    try:
                        path = '/home/openerp/model_pdf/' + cr.dbname
                        store_fname = mail_template_obj._get_random_fname(path)
                        file_url = os.path.join(path, store_fname)
                        fp = open(file_url, 'wb')
                        file_str = base64.decodestring(compose.file)
                        try:
                            fp.write(file_str)
                        finally:    
                            fp.close()
                    except Exception, e:
                        raise osv.except_osv('Erreur!', str(e))
                    mail_template_obj.write(cr, uid, compose.lettre_id.id, {'file_url': file_url})
                else:
                    raise osv.except_osv('Attention', u'Il faut ajouter un fichier pdf comme mod\u00E8le du courrier')
            generated_pdf = pypdftk.fill_form(file_url, datas)
            os.rename(generated_pdf, generated_pdf + '.pdf')
            with open(generated_pdf + '.pdf', "rb") as encode:
                encoded_file = base64.b64encode(encode.read())
            self.write(cr, uid, ids, {'res_file': encoded_file, 'res_file_name': 'Courrier.pdf'})

        view = model_obj.get_object_reference(cr, uid, 'of_gesdoc', 'view_courrier_wizard2_file')
        return {
            'name': 'Envoyer un courrier',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view[1],
            'res_model': 'of.compose.mail',
            'src_model': context['model'],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids[0],
            'context': context,
        }

    def close_wizard(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.act_window_close'}

    def onchange_chp_tmp(self, cr, uid, ids, chp_tmp_ids=False, len_chp_tmp=0):
        if chp_tmp_ids:
            new_len = 0
            for chp in chp_tmp_ids:
                if len(chp) >= 2:
                    if chp[0] in (2, 3):
                        raise osv.except_osv('Attention', u'Merci de configurer le mod\u00E8le du courrier pour supprimer ou ajouter les champs')
                    elif chp[0] in (0, 1, 4, 6):
                        new_len += 1
            if new_len != len_chp_tmp:
                raise osv.except_osv('Attention', u'Merci de configurer le mod\u00E8le du courrier pour supprimer ou ajouter les champs')
        else:
            if len_chp_tmp != 0:
                raise osv.except_osv('Attention', u'Merci de configurer le mod\u00E8le du courrier pour supprimer ou ajouter les champs')

class of_gesdoc_chp_tmp(osv.AbstractModel):
    _name = 'of.gesdoc.chp.tmp'
    _description = 'PDF champs temporaire'
    
    _columns = {
        'name': fields.char('Nom du champ PDF', size=256, required=True, readonly=True),
        'value_openfire': fields.char('Valeur OpenFire', size=256),
        'compose_id': fields.many2one('of.compose.mail', 'Visualisation Courrier'),
    }
