# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError

import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
import pypdftk
import os
import base64

class of_compose_mail(models.TransientModel):
    _name = 'of.compose.mail'
    _description = 'Courrier'

    lettre_id = fields.Many2one('of.mail.template', string=u'Modèle')
    content = fields.Text(string='Contenu')
    file = fields.Binary(related="lettre_id.file", string=u'Modèle PDF', store=False)
    file_name = fields.Char(related="lettre_id.file_name", string='Nom du fichier', size=64)
    res_file = fields.Binary(string=u'Fichier complété', readonly=True)
    res_file_name = fields.Char(string=u'Nom du fichier résultat', size=64)
    chp_tmp_ids = fields.One2many('of.gesdoc.chp.tmp', 'compose_id', string='Liste des champs')

    @api.model
    def format_body(self, body):
        return (body or u'').encode('utf8', 'ignore')

    @api.onchange('lettre_id')
    def _onchange_lettre_id(self):
        lettre = self.lettre_id
        if not lettre:
            return

        obj = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        values = self._get_dict_values(obj)

        if lettre.file:
            self.chp_tmp_ids = [
                (0, 0, {
                    'name': chp.name or '',
                    'value_openfire': chp.to_export and chp.value_openfire and self.format_body(chp.value_openfire % values) or '',
                })
                for chp in lettre.chp_ids
            ]
        else:
            self.content = self.format_body((lettre.body_text or '') % values)

    @api.model
    def _get_objects(self, o):
        partner_obj = self.env['res.partner']

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
        address = addresses['contact'] and partner_obj.browse(addresses['contact'])
        address_pose = addresses['delivery'] and partner_obj.browse(addresses['delivery'])

        result = {
            'address_pose': address_pose,
            'address'     : address,
            'partner'     : partner,
            'order'       : order,
            'invoice'     : invoice,
        }
        return result

    @api.model
    def _get_dict_values(self, o, objects=None):
        if not o:
            return {}
        lang_obj = self.env['res.lang']

        if not objects:
            objects = self._get_objects(o)
        order = objects.get('order',False)
        invoice = objects.get('invoice',False)
        partner = objects.get('partner',False)
        address = objects.get('address',False)
        address_pose = objects.get('address_pose',False)

        lang_code = self._context.get('lang', partner.lang)
        lang = lang_obj.search([('code','=', lang_code)])

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
            'c_name'            : address and (address.name or (address.partner_id and address.partner_id.name)) or '',
            'c_street'          : address and address.street or '',
            'c_street2'         : address and address.street2 or '',
            'c_zip'             : address and address.zip or '',
            'c_city'            : address and address.city or '',
            'c_phone'           : address and address.phone or '',
            'c_mobile'          : address and address.mobile or '',
            'c_fax'             : address and address.fax or '',
            'c_email'           : address and address.email or '',
            'c_adr_pose_name'   : address_pose and (address_pose.name or (address_pose.partner_id and address_pose.partner_id.name)) or '',
            'c_adr_pose_street' : address_pose and address_pose.street or '',
            'c_adr_pose_street2': address_pose and address_pose.street2 or '',
            'c_adr_pose_city'   : address_pose and address_pose.city or '',
            'c_adr_pose_zip'    : address_pose and address_pose.zip or '',
            'date'              : time.strftime('%d/%m/%Y'),
        })

        date_length = len((datetime.now()).strftime(DEFAULT_SERVER_DATE_FORMAT))
        for date_field in ('date_order', 'date_confirm_order', 'date_invoice'):
            if not res[date_field]:
                continue
            # reformatage de la date (copie depuis report_sxw : rml_parse.formatLang())
            date = datetime.strptime(res[date_field][:date_length], DEFAULT_SERVER_DATE_FORMAT)
            date = date.strftime(lang.date_format.encode('utf-8'))
            res[date_field] = date
        return res

    def _get_model_action_dict(self):
        return {
            'res.partner'    : 'of_gesdoc.courriers',
            'sale.order'     : 'of_gesdoc.courriers_sale',
            'crm.lead'       : 'of_gesdoc.courriers_crm',
            'account.invoice': 'of_gesdoc.courriers_account',
        }

    #print a mail in the format pdf
    @api.multi
    def print_report(self):
        lettre_obj = self.env['of.mail.template']
        tmp = self.read()
        data = {
            'ids' : self._context.get('data_ids', []),
            'model' : self._context.get('model', []),
            'form' : tmp and tmp[0] or {},
        }
        lett_id = data['form']['lettre_id'][0]
        obj = self.env[data['model']]
        lettre = lettre_obj.browse(lett_id)
        for o in obj.browse(data['ids']):
            #information of customer
            partner = o if data['model'] == 'res.partner' else o.partner_id
            if partner.child_ids:
                partner = partner.child_ids[0]

            #Update partner comment
            text = "%s: Envoi d'un courrier \"%s\" (%s)\n" % (time.strftime('%Y-%m-%d'),
                                                              lettre.name_get()[0][1],
                                                              self.env.user.name_get()[0][1])

            comment = partner.comment or ''
            if comment and comment[-1] != '\n':
                text = '\n' + text
            partner.comment = partner.comment + text

        #test if user has checked 'sans adresse' and 'sans entete'
        #self._log_event(cr, uid, ids, data, context=context)
        act = self._get_model_action_dict().get(data['model'], '')
        if lettre.sans_header:
            act += '_sehead'
        elif lettre.sans_add:
            act += '_se'
        return {
            'type'       : 'ir.actions.report.xml',
            'report_name': act,
            'datas'      : data,
        }

    @api.multi
    def print_report_acrobat(self):
        if self:
            datas = {}
            for chp in self.chp_tmp_ids:
                datas[chp.name or ''] = chp.value_openfire or ''

            attachment_obj = self.env['ir.attachment']
            attachment = attachment_obj.search([('res_model', '=', self.lettre_id._name),
                                                ('res_field', '=', 'file'),
                                                ('res_id', '=', self.lettre_id.id)])
            if not attachment:
                raise UserError(u'Ce modèle de courrier ne contient pas de document pdf')

            # Generation du fichier rempli. Le parametre flatten (True par defaut) retire la possibilite de modifier le document pdf genere
            file_path = attachment_obj._full_path(attachment.store_fname)
            generated_pdf = pypdftk.fill_form(file_path, datas, flatten=not self.lettre_id.fillable)
            os.rename(generated_pdf, generated_pdf + '.pdf')
            with open(generated_pdf + '.pdf', "rb") as encode:
                encoded_file = base64.b64encode(encode.read())
            # Si c'est un rapport généré depuis un SAV, on prend le no du SAV et le nom du client
            if self._context['model'] == 'project.issue' and 'cnom' in datas and 'sno' in datas and datas['cnom'] and datas['sno']:
                res_file_name = datas['sno'] + ' ' + datas['cnom'] + '.pdf'
            elif self._context['model'] == 'project.issue' and '1_Client_Nom' in datas and '1_num_sav' in datas and datas['1_Client_Nom'] and datas['1_num_sav']:
                res_file_name = datas['1_num_sav'] + ' ' + datas['1_Client_Nom'] + '.pdf'
            else:
                res_file_name = 'courrier.pdf'
            self.write({'res_file': encoded_file, 'res_file_name': res_file_name})

        view = self.env.ref('of_gesdoc.view_courrier_wizard')
        return {
            'name': 'Envoyer un courrier',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': 'of.compose.mail',
            'src_model': self._context['model'],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
            'context': self._context,
        }

class of_gesdoc_chp_tmp(models.TransientModel):
    _name = 'of.gesdoc.chp.tmp'
    _description = 'PDF champs temporaire'

    name = fields.Char(string='Nom du champ PDF', size=256, required=True, readonly=True)
    value_openfire = fields.Char(string='Valeur OpenFire', size=256)
    compose_id = fields.Many2one('of.compose.mail', string='Visualisation Courrier')
