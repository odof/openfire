# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.addons.mail.models.mail_template import format_date, format_tz, format_amount

import dateutil.relativedelta as relativedelta
import datetime
from urllib import urlencode, quote as quote
import time
import tempfile
import os
import base64
import logging
import re
import copy
import fitz

_logger = logging.getLogger(__name__)

try:
    import pypdftk
except ImportError:
    pypdftk = None

# Code copié depuis odoo/addons/mail/models/mail_template.py avec modification pour désactiver les échappements xml/html
try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=False,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': quote,
        'urlencode': urlencode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': reduce,
        'map': map,
        'round': round,
        'cmp': cmp,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),

        # Ajout d'éléments OpenFire
        'hasattr': hasattr,
        'getattr': getattr,
    })
    mako_safe_template_env = copy.copy(mako_template_env)
    mako_safe_template_env.autoescape = False
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")


class OfComposeMail(models.TransientModel):
    _name = 'of.compose.mail'
    _description = 'Courrier'

    lettre_id = fields.Many2one('of.mail.template', string=u'Modèle')
    content = fields.Text(string='Contenu')
    res_file = fields.Binary(string=u'Fichier complété', readonly=True)
    res_file_name = fields.Char(string=u'Nom du fichier résultat', size=64)
    chp_tmp_ids = fields.One2many('of.gesdoc.chp.tmp', 'compose_id', string='Liste des champs')

    @api.model
    def format_body(self, body):
        return (body or u'').encode('utf8', 'ignore')

    @api.model
    def _eval_text(self, value, values):
        if not value:
            return False
        #   Rétro-compatibilité
        # Transformation de l'ancien système %( )s en ${ }
        value = re.sub(r'%\((.*?)\)s', r'${\1}', value)
        # Transformation des échappements %% en simple %
        value = re.sub(r'%%', r'%', value)

        # Interprétation du code avec l'aide de jinja2 (récupéré de odoo mail_template.py)
        template = mako_template_env.from_string(tools.ustr(value))

        try:
            result = template.render(values)
        except Exception:
            _logger.info(u"Échec de l'interprétation du code %r en utilisant les valeurs %r" % (template, values),
                         exc_info=True)
            raise UserError(u"Échec de l'interprétation du code %r en utilisant les valeurs %r" % (template, values))

        if result == u"False":
            result = u""
        return result

    @api.model
    def eval_champs(self, obj, champs):
        u"""
        :param obj: Objet (instance avec id unique) pour lequel est généré le courrier
        :param champs: Instances de of.gesdoc.chp ou de of.gesdoc.chp.tmp
        :return: Liste de tuples [('nom du champ', 'valeur à afficher dans le courrier')]
        """
        champs = champs.filtered(lambda x: not x.name.endswith('_af_image'))
        objects = self._get_objects(obj)
        values = self._get_dict_values(obj, objects)
        result = []
        for chp in champs:
            result.append((
                chp.name or '',
                chp.to_export and self._eval_text(chp.value_openfire, values) or '',
            ))
        return result

    @api.model
    def eval_image_champs(self, obj, champs):
        u"""
        :param obj: Objet (instance avec id unique) pour lequel est généré le courrier
        :param champs: Instances de of.gesdoc.chp ou de of.gesdoc.chp.tmp
        :return: Liste de tuples [(of.gesdoc.chp, image associée)]
        """
        objects = self._get_objects(obj)
        values = self._get_dict_values(obj, objects)
        result = []

        for chp in champs:
            value = chp.value_openfire and chp.value_openfire.strip('$').strip('{').strip('}') or ""
            result.append((
                chp,
                chp.to_export and value and safe_eval(value, values) or "",
            ))
        return result

    @api.model
    def _insert_images(self, obj, pdf_path, chp_ids):
        # Filtrage des champs sur la norme acrobat reader, le champ termine par _af_image
        image_data = dict(self.eval_image_champs(obj, chp_ids.filtered(lambda x: x.name.endswith('_af_image'))))
        doc = fitz.open(pdf_path)

        for field, content in image_data.items():
            content_base64 = None
            if isinstance(content, str):
                # Si le contenu est une string, on considère que l'image
                # est une signature encodée base64
                content_base64 = content
            elif hasattr(content, 'data'):
                # on va considèrer sinon que c'est une image
                content_base64 = content.data

            if content_base64 and (abs(field.x1 - field.x0) > 0) and (abs(field.y1 - field.y0) > 0):
                # on récupère toutes les infos du cadre et de l'image pour faire nos calculs
                start_x = field.x0
                end_x = field.x1
                start_y = field.y0
                end_y = field.y1
                width = abs(field.x1 - field.x0)
                height = abs(field.y1 - field.y0)
                img = base64.b64decode(content_base64)
                pix = fitz.Pixmap(bytearray(img))
                # si les valeurs du cadre sont supérieures ou égales a celles de l'images, pas de resize à faire
                ratio_w = width / pix.width
                ratio_h = height / pix.height
                h_to_move = 0.0
                w_to_move = 0.0
                # un resize du cadre est a faire car au moins une des deux valeurs de l'image est plus grande que
                # celle du cadre. On utilise que le ratio le plus petit car le insertImage rempli totalement le cadre
                if ratio_w < 1 or ratio_h < 1:
                    if ratio_w < ratio_h:
                        h_to_move = (height - ratio_w * pix.height) / 2
                    else:
                        w_to_move = (width - ratio_h * pix.width) / 2
                else:
                    h_to_move = (height - pix.height) / 2
                    w_to_move = (width - pix.width) / 2
                # on bouge les points du cadre ce qui a pour effet de changer la taille de l'image
                end_y -= h_to_move
                start_y += h_to_move
                end_x -= w_to_move
                start_x += w_to_move
                page = doc[field.page_number]
                page_height = page.rect[3]
                # on créer le cadre et on insère l'image
                rect = fitz.Rect(start_x, page_height - end_y, end_x, page_height - start_y)
                page.insertImage(rect, pixmap=pix)

        doc.saveIncr()
        doc.close()

    @api.model
    def eval_text(self, obj, text):
        objects = self._get_objects(obj)
        values = self._get_dict_values(obj, objects)
        return self.format_body(self._eval_text(text, values)) or ''

    @api.onchange('lettre_id')
    def _onchange_lettre_id(self):
        lettre = self.lettre_id
        if not lettre:
            return

        obj = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))

        if lettre.file:
            self.chp_tmp_ids = [
                (0, 0, {
                    'name': chp[0],
                    'value_openfire': self.format_body(chp[1]) if isinstance(chp[1], basestring) else chp[1]
                })
                for chp in self.eval_champs(obj, lettre.chp_ids)
            ] + [
                (0, 0, {
                    'name': chp[0].name,
                    'value_openfire': chp[1] and "image" or ""
                })
                for chp in self.eval_image_champs(obj, lettre.chp_ids.filtered(lambda x: x.name.endswith('_af_image')))
            ]
        else:
            self.chp_tmp_ids = []
            self.content = self.eval_text(obj, lettre.body_text)

    @api.model
    def _get_objects(self, o):
        partner_obj = self.env['res.partner']

        partner = o if o._name == 'res.partner' else getattr(o, 'partner_id', partner_obj)
        order = self.env['sale.order']
        invoice = self.env['account.invoice']

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

        addresses = partner.address_get(adr_pref=['contact', 'delivery'])
        address = addresses['contact'] and partner_obj.browse(addresses['contact']) or partner_obj
        address_pose = addresses['delivery'] and partner_obj.browse(addresses['delivery']) or partner_obj
        cal_event = self.env['calendar.event']
        if partner:
            cal_event = cal_event.search([('partner_ids', 'in', [partner.id])], order='start DESC', limit=1)

        result = {
            'address_pose': address_pose,
            'address'     : address,
            'partner'     : partner,
            'order'       : order,
            'invoice'     : invoice,
            'cal_event'   : cal_event,
        }
        return result

    @api.model
    def _get_dict_values(self, o, objects):
        if not o:
            return {}
        lang_obj = self.env['res.lang']

        order = objects['order']
        invoice = objects['invoice']
        partner = objects['partner']
        address = objects['address']
        address_pose = objects['address_pose']
        cal_event = objects['cal_event']

        lang_code = self._context.get('lang', partner.lang)
        lang = lang_obj.search([('code', '=', lang_code or 'fr_FR')])

        values = (
            ('amount_total', o, ''),
            ('origin', o, ''),
            ('date_order', order or o, ''),
            ('confirmation_date', order or o, ''),
            ('date_invoice', invoice or o, ''),
            ('residual', invoice or o, ''),
            ('number', invoice, ''),
            ('user_id', o, ''),
            ('objet', o, ''),
        )

        res = {key: getattr(obj, key, default) or default for key, obj, default in values}

        res['date_confirm_order'] = res['confirmation_date']
        del res['confirmation_date']
        res['user_name'] = res['user_id'] and res['user_id'].name
        del res['user_id']

        if cal_event:
            date_event = fields.Datetime.from_string(cal_event.start)
            date_event = fields.Datetime.context_timestamp(self, date_event)

        date_format = lang.date_format.encode('utf-8')
        res.update({
            'c_title'                   : address.title.name or 'Madame, Monsieur',
            'c_name'                    : address.name or (address.parent_id and address.parent_id.name) or '',
            'c_note'                    : partner.comment,
            'c_street'                  : address.street or '',
            'c_street2'                 : address.street2 or '',
            'c_zip'                     : address.zip or '',
            'c_city'                    : address.city or '',
            'c_phone'                   : address.phone or '',
            'c_mobile'                  : address.mobile or '',
            'c_fax'                     : address.fax or '',
            'c_email'                   : address.email or '',
            'c_adr_intervention_name'   : address_pose.name or address_pose.parent_id.name or '',
            'c_adr_intervention_street' : address_pose.street or '',
            'c_adr_intervention_street2': address_pose.street2 or '',
            'c_adr_intervention_city'   : address_pose.city or '',
            'c_adr_intervention_zip'    : address_pose.zip or '',
            'c_rdv_date'                : cal_event and date_event.strftime(date_format) or '',
            'c_rdv_heure'               : cal_event and date_event.strftime('%H:%M') or '',
            'date'                      : time.strftime(date_format),
            'order_name'                : order and order.name or '',
        })

        for date_field in ('date_order', 'date_confirm_order', 'date_invoice'):
            if not res[date_field]:
                continue

            date = fields.Datetime.from_string(res[date_field])
            date = date.strftime(date_format)
            res[date_field] = date

        # Pour rétrocompatibilité
        res.update({
            'c_adr_pose_name'   : res['c_adr_intervention_name'],
            'c_adr_pose_street' : res['c_adr_intervention_street'],
            'c_adr_pose_street2': res['c_adr_intervention_street2'],
            'c_adr_pose_city'   : res['c_adr_intervention_city'],
            'c_adr_pose_zip'    : res['c_adr_intervention_zip'],
        })

        res.update(objects)
        res.update({
            'o': o,
            'format_date': lambda date, format=False, context=self._context: format_date(self.env, date, format),
            'format_tz': lambda dt, tz=False, format=False, context=self._context: format_tz(self.env, dt, tz, format),
            'format_amount': lambda amount, currency, context=self._context: format_amount(self.env, amount, currency),
            'user': self.env.user,
            'ctx': self._context,  # context kw would clash with mako internals
        })
        return res

    def _get_model_action_dict(self):
        return {
            'res.partner'    : 'of_gesdoc.courriers',
            'sale.order'     : 'of_gesdoc.courriers_sale',
            'crm.lead'       : 'of_gesdoc.courriers_crm',
            'account.invoice': 'of_gesdoc.courriers_account',
        }

    # print a mail in the format pdf
    @api.multi
    def print_report(self):
        lettre_obj = self.env['of.mail.template']
        tmp = self.read()
        data = {
            'ids' : self._context.get('active_ids', []),
            'model' : self._context.get('model', []),
            'form' : tmp and tmp[0] or {},
        }
        lett_id = data['form']['lettre_id'][0]
        obj = self.env[data['model']]
        lettre = lettre_obj.browse(lett_id)
        for o in obj.browse(data['ids']):
            # information of customer
            partner = o if data['model'] == 'res.partner' else o.partner_id
            if not partner:
                continue
            if partner.child_ids:
                partner = partner.child_ids[0]

            # Update partner comment
            text = "%s: Envoi d'un courrier \"%s\" (%s)\n" % (time.strftime('%Y-%m-%d'),
                                                              lettre.name_get()[0][1],
                                                              self.env.user.name_get()[0][1])

            comment = partner.comment or ''
            if comment and comment[-1] != '\n':
                text = '\n' + text
            partner.comment = comment + text

        # test if user has checked 'sans adresse' and 'sans entete'
        # self._log_event(cr, uid, ids, data, context=context)
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
            fd, generated_pdf = tempfile.mkstemp(prefix='gesdoc_', suffix='.pdf')
            try:
                obj = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
                self.fill_form(obj, file_path, datas, generated_pdf, self.lettre_id)
                with open(generated_pdf, "rb") as encode:
                    encoded_file = base64.b64encode(encode.read())
            finally:
                os.close(fd)
                try:
                    os.remove(generated_pdf)
                except Exception:
                    pass
            # Si c'est un rapport généré depuis un SAV, on prend le no du SAV et le nom du client
            if self._context['model'] == 'project.issue' and datas.get('cnom') and datas.get('sno'):
                res_file_name = datas['sno'] + ' ' + datas['cnom'] + '.pdf'
            elif self._context['model'] == 'project.issue' and datas.get('1_Client_Nom') and datas.get('1_num_sav'):
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

    @api.model
    def fill_form(self, obj, file_path, data, generated_pdf, mail_template):
        pypdftk.fill_form(file_path, data, out_file=generated_pdf, flatten=not mail_template.fillable)
        self._insert_images(obj, generated_pdf, mail_template.chp_ids)


class OfGesdocChpTmp(models.TransientModel):
    _name = 'of.gesdoc.chp.tmp'
    _description = 'PDF champs temporaire'

    name = fields.Char(string='Nom du champ PDF', required=True, readonly=True)
    value_openfire = fields.Char(string='Valeur OpenFire')
    compose_id = fields.Many2one('of.compose.mail', string='Visualisation Courrier')
