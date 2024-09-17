# -*- coding: utf-8 -*-

import logging
from odoo.exceptions import UserError
from odoo import api, fields, models
from HTMLParser import HTMLParser
import urllib
import json

_logger = logging.getLogger(__name__)


class OFSmsCompose(models.TransientModel):
    _name = "of.sms.compose"

    @api.model
    def default_get(self, fields_list):
        result = super(OFSmsCompose, self).default_get(fields_list)
        from_mobile_id = self.env['of.sms.account'].search([], limit=1)
        if not from_mobile_id:
            raise UserError(u"Erreur ! (#ED100)\n\nAucun émetteur SMS trouvé. Les émetteurs se configurent dans le "
                            u"menu Configuration/SMS/Comptes émetteurs.")
        result['from_mobile_id'] = from_mobile_id.id
        active_model = self._context.get('active_model', '')

        # en cas d'erreur d'envoi à un seul partenaire le pop-up est actualisé
        if active_model != 'of.sms.compose':
            result['model'] = active_model
            result['partner_field'] = 'partner_id'
            record_ids = self._context.get('active_ids', '')
            result['record_ids'] = json.dumps(record_ids)
            result['record_id'] = self._context.get('active_id', '')
            if active_model == u'res.partner':
                result['partner_ids'] = record_ids
                result['partner_field'] = False
            elif active_model == u'crm.lead':
                result['lead_ids'] = record_ids
            elif active_model == u'of.planning.intervention':
                result['intervention_ids'] = record_ids
            elif active_model == u'sale.order':
                result['order_ids'] = record_ids
            elif active_model == u'account_invoice':
                result['invoice_ids'] = record_ids

        return result

    error_message = fields.Text(readonly=True)
    success_message = fields.Char(readonly=True)
    queued_message = fields.Char(readonly=True)
    record_id = fields.Integer()
    record_ids = fields.Char(help=u"chaine de caractères représentant les ids sous forme '[id1, id2, ..]'")
    partner_ids = fields.Many2many('res.partner', string="Destinataires")
    partner_field = fields.Char(help=u"Nom du champ partenaire dans le res_model")
    # On créé un champ par res_model possible pour pouvoir facilement ajouter / supprimer des destinataires
    lead_ids = fields.Many2many('crm.lead', string="Destinataires")
    intervention_ids = fields.Many2many('of.planning.intervention', string="Destinataires")
    order_ids = fields.Many2many('sale.order', string="Destinataires")
    invoice_ids = fields.Many2many('account.invoice', string="Destinataires")
    record_nb = fields.Integer(string=u"Nombre d'enregistrements", compute="_compute_record_nb")
    model = fields.Char(help=u"nom du res_model")
    sms_template_id = fields.Many2one('of.sms.template', string=u"Modèle")
    from_mobile_id = fields.Many2one('of.sms.number', required=True, string=u"Émetteur mobile")
    to_number = fields.Char(string=u'No mobile destinaire', readonly=True)
    sms_content = fields.Text(string=u'Contenu SMS')
    sms_content_previ = fields.Text(string=u'Prévisualisation', compute="_compute_sms_content_previ")
    media_id = fields.Binary(
        string=u"Media (MMS)")  # Non utilisé. Laissé pour cause de compatibilité avec code d'origine.
    media_filename = fields.Char(string=u"Media filename")
    delivery_time = fields.Datetime(string=u"Date d'envoi")
    is_commercial = fields.Boolean(
        u'Est commercial',
        help=u"Indique si le texto est commercial.\nSi oui, un message de désinscription sera ajouté à la fin "
             u"du message et ne sera envoyé que du lundi au samedi 8h-20h.\nNote : la loi réprime pénalement "
             u"le fait d'envoyer des textos non liés à l'exécution du contrat sans ces mentions.")
    show_previ = fields.Boolean(string=u"Montrer la prévisualisation")
    show_desti = fields.Boolean(string=u"Montrer les destinataires")
    all_passed = fields.Boolean(string=u"aucun echec")

    @api.depends('record_ids')
    def _compute_record_nb(self):
        for wizard in self:
            wizard.record_nb = len(json.loads(wizard.record_ids))

    @api.depends('sms_content', 'model', 'record_id')
    def _compute_sms_content_previ(self):
        for wizard in self:
            try:
                # On passe le contenu du texto par l'interpréteur Mako.
                content = self.env['mail.template'].render_template(
                    self.sms_content, self.model, self.record_id, post_process=False)
                wizard.sms_content_previ = HTMLParser().unescape(content)
            except Exception:
                wizard.sms_content_previ =\
                    u"Erreur de rendu du contenu du sms. Vérifiez vos variables ${object.champ or ''}"

    @api.onchange('sms_template_id')
    def _onchange_sms_template_id(self):
        """Prefills from mobile, sms_account and sms_content but allow them to manually change the content after"""
        if self.sms_template_id:
            self.from_mobile_id = self.sms_template_id.from_mobile_verified_id.id
            self.media_id = self.sms_template_id.media_id
            self.media_filename = self.sms_template_id.media_filename
            self.sms_content = self.sms_template_id.template_body

    @api.onchange('lead_ids', 'intervention_ids', 'order_ids', 'invoice_ids')
    def _onchange_destinataires(self):
        self.ensure_one()
        if self.lead_ids:
            self.partner_ids = self.lead_ids.mapped('partner_id')
        elif self.intervention_ids:
            self.partner_ids = self.intervention_ids.mapped('partner_id')
        elif self.order_ids:
            self.partner_ids = self.order_ids.mapped('partner_id')
        elif self.invoice_ids:
            self.partner_ids = self.invoice_ids.mapped('partner_id')

    @api.multi
    def send_entity(self):
        """
        Attempts to send the sms.
        Logs successfully sent smses.
        Errors will be shown to the user.
        """
        self.ensure_one()

        # convertir la chaine de caractères contenant les ids en list d'ids
        record_ids = json.loads(self.record_ids)
        # Create the queued sms
        my_model = self.env['ir.model'].search([('model', '=', self.model)])
        my_obj = self.env[self.model]
        records = my_obj.browse(record_ids)
        records_failed = self.env[self.model]
        status_dict = {}
        error_dict = {}

        for record in records:
            partner = self.partner_field and record[self.partner_field] or record
            # process content
            try:
                to_number = partner.get_mobile_numbers()
                # On passe le contenu du texto par l'interpréteur Mako.
                content = self.env['mail.template'].render_template(
                    self.sms_content, self.model, record.id, post_process=False)
                sms_content = HTMLParser().unescape(content)
                status_code = 'queued'
                # Envoyer le SMS directement si il n'y a pas d'heure d'envoi ni d'erreur de rendu du template
                if not self.delivery_time:
                    my_sms = self.from_mobile_id.account_id.send_message(
                        self.from_mobile_id.mobile_number, ','.join(to_number), sms_content, self.model, record.id,
                        self.media_id, media_filename=self.media_filename, is_commercial=self.is_commercial)
                    status_code = my_sms.delivery_state
                    if status_code == 'failed':
                        records_failed |= record
                        if my_sms.human_read_error != "":
                            if error_dict.get(my_sms.human_read_error):
                                error_dict[my_sms.human_read_error] += 1
                            else:
                                error_dict[my_sms.human_read_error] = 1
                        else:
                            if error_dict.get(my_sms.response_string):
                                error_dict[my_sms.response_string] += 1
                            else:
                                error_dict[my_sms.response_string] = 1
                if status_dict.get(status_code):
                    status_dict[status_code] += 1
                else:
                    status_dict[status_code] = 1
                # Créer le message dans le suivi
                self.env['of.sms.message'].create({
                    'record_id': record.id,
                    'model_id': my_model[0].id,
                    'account_id': self.from_mobile_id.account_id.id,
                    'from_mobile': self.from_mobile_id.mobile_number,
                    'to_mobile': ','.join(to_number),
                    'sms_content': sms_content,
                    'status_string': '-',
                    'direction': 'O',
                    'message_date': self.delivery_time,
                    'status_code': status_code,
                    'by_partner_id': self.env.user.partner_id.id,
                    'is_commercial': self.is_commercial
                })
            except Exception as e:
                if status_dict.get('exception'):
                    status_dict['exception'] += 1
                else:
                    status_dict['exception'] = 1
                e_name = getattr(e, 'name', False)
                if e_name:
                    if error_dict.get(e_name):
                        error_dict[e_name] += 1
                    else:
                        error_dict[e_name] = 1
                else:
                    if error_dict.get(u"Erreur de rendu du contenu du sms"):
                        error_dict[u"Erreur de rendu du contenu du sms"] += 1
                    else:
                        error_dict[u"Erreur de rendu du contenu du sms"] = 1
                records_failed |= record
                continue

        # Informations à afficher
        # Réussites
        nb_records_success = status_dict.get('successful', 0)
        if nb_records_success:
            pluriel = nb_records_success > 1 and u"s" or u""
            success_message = u"%s SMS envoyé%s avec succès" % (nb_records_success, pluriel)
        else:
            success_message = u""
        # envois différés
        nb_record_queued = status_dict.get('queued', 0)
        if nb_record_queued:
            pluriel = nb_record_queued > 1 and u"s" or u""
            queued_message = u"%s SMS programmé%s pour envoi différé" % (nb_record_queued, pluriel)
        else:
            queued_message = u""

        # Préparer les champs pour ré-ouvrir le pop-up
        context = {
            'default_model': self.model,
            'default_queued_message': queued_message,
            'default_success_message': success_message,
            'default_show_previ': self.show_previ,
            'default_show_desti': self.show_desti,
            'default_sms_content': self.sms_content,
            'default_all_passed': True,
        }
        # Pour savoir si masquer les champs d'envoi
        if records_failed:
            context['default_record_id'] = records_failed[0].id
            context['default_record_ids'] = json.dumps(records_failed.ids)
            context['default_partner_field'] = self.partner_field or False
            context['default_partner_ids'] = self.partner_ids and records_failed.ids or False
            context['default_lead_ids'] = self.lead_ids and records_failed.ids or False
            context['default_intervention_ids'] = self.intervention_ids and records_failed.ids or False
            context['default_order_ids'] = self.order_ids and records_failed.ids or False
            context['default_invoice_ids'] = self.invoice_ids and records_failed.ids or False
            context['default_all_passed'] = False
            error_message = u"%s SMS en echec:" % len(records_failed)
            for k in error_dict:
                error_message += u'\n  "%s": %d' % (k, error_dict[k])
            context['default_error_message'] = error_message

        return {
            'type'     : 'ir.actions.act_window',
            'res_model': 'of.sms.compose',
            'view_type': 'form',
            'view_mode': 'form',
            'target'   : 'new',
            'context'  : context,
            }
