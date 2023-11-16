# -*- coding: utf-8 -*-

import logging
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models
import re
import requests
from HTMLParser import HTMLParser
import urllib
import json
from odoo.addons.of_base.models.partner import convert_phone_number

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
except ImportError:
    _logger.debug(u"Impossible d'importer la librairie Python 'phonenumbers'.")


class OFSmsTemplate(models.Model):
    _name = "of.sms.template"

    name = fields.Char(required=True, string=u'Nom modèle', translate=True)
    model_id = fields.Many2one(
        'ir.model', string=u'Appliquer à', help="The kind of document with with this template can be used")
    model = fields.Char(related="model_id.model", string=u'Related Document Model', store=True, readonly=True)
    template_body = fields.Text(
        string='Body', translate=True, help=u"Plain text version of the message (placeholders may be used here)")
    sms_from = fields.Char(
        string=u'Émetteur (mobile)',
        help=u"Sender mobile number (placeholders may be used here). "
             u"If not set, the default value will be the author's mobile number.")
    sms_to = fields.Char(string=u'Destinataire (Mobile)', help=u"To mobile number (placeholders may be used here)")
    account_gateway_id = fields.Many2one('of.sms.account', string=u"Compte")
    model_object_field_id = fields.Many2one(
        'ir.model.fields', string=u"Champ",
        help=u"Select target field from the related document model.\n"
             u"If it is a relationship field you will be able to select a target field at the destination of the "
             u"relationship.")
    sub_object_id = fields.Many2one(
        'ir.model', string=u'Sous-modèle', readonly=True,
        help=u"When a relationship field is selected as first field, this field shows the document model the "
             u"relationship goes to.")
    sub_model_object_field_id = fields.Many2one(
        'ir.model.fields', string=u'Sous-champ',
        help="When a relationship field is selected as first field, this field lets you select the target field within "
             "the destination document model (sub-model).")
    null_value = fields.Char(string=u'Valeur par défaut', help=u"Optional value to use if the target field is empty")
    copyvalue = fields.Char(
        string=u'Placeholder Expression',
        help=u"Final placeholder expression, to be copy-pasted in the desired template field.")
    from_mobile_verified_id = fields.Many2one('of.sms.number', string=u"From Mobile (stored)")
    from_mobile = fields.Char(string="Émetteur", help=u"Placeholders are allowed here")
    # Champs media (PJ d'un SMS) laissés pour compatibilité code d'origine
    media_id = fields.Binary(string=u"Media (MMS)")
    media_filename = fields.Char(string=u"Media filename")
    media_ids = fields.Many2many('ir.attachment', string=u"Media (MMS)[Automated actions only]")

    @api.onchange('model_object_field_id')
    def _onchange_model_object_field_id(self):
        if self.model_object_field_id.relation:
            self.sub_object_id = self.env['ir.model'].search([('model', '=', self.model_object_field_id.relation)])[
                0].id
        else:
            self.sub_object_id = False

        if self.model_object_field_id:
            self.copyvalue = self.build_expression(self.model_object_field_id.name, self.sub_model_object_field_id.name,
                                                   self.null_value)

    @api.onchange('sub_model_object_field_id')
    def _onchange_sub_model_object_field_id(self):
        if self.sub_model_object_field_id:
            self.copyvalue = self.build_expression(self.model_object_field_id.name, self.sub_model_object_field_id.name,
                                                   self.null_value)

    @api.onchange('from_mobile_verified_id')
    def _onchange_from_mobile_verified_id(self):
        if self.from_mobile_verified_id:
            self.from_mobile = self.from_mobile_verified_id.mobile_number

    @api.multi
    def send_sms(self, record_ids):
        """Send the sms using all the details in this sms template, using the specified record ID"""
        self.ensure_one()
        h = HTMLParser()
        for record_id in record_ids:
            rendered_sms_template_body = h.unescape(
                self.env['of.sms.template'].render_template(self.template_body, self.model_id.model, record_id))
            rendered_sms_to = h.unescape(
                self.env['of.sms.template'].render_template(self.sms_to, self.model_id.model, record_id))
            # Queue the SMS message since we can't directly send MMS
            self.env['of.sms.message'].create({
                'record_id': record_id,
                'model_id': self.model_id.id,
                'account_id': self.from_mobile_verified_id.account_id.id,
                'from_mobile': self.from_mobile,
                'to_mobile': rendered_sms_to,
                'sms_content': rendered_sms_template_body,
                'direction': 'O',
                'message_date': datetime.utcnow(),
                'status_code': 'queued',
            })
            # Turn the queue manager on
            self.env['ir.model.data'].get_object('of_sms', 'sms_queue_check').active = True

    @api.model
    def build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
           based on the values provided in the placeholder assistant.

          :param field_name: main field name
          :param sub_field_name: sub field name (M2O)
          :param null_value: default value if the target value is empty
          :return: final placeholder expression
        """
        expression = ''
        if field_name:
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression


class OFSmsMessage(models.Model):
    _name = "of.sms.message"
    _order = "message_date desc"

    record_id = fields.Integer(readonly=True, string=u"Enregistrement")
    account_id = fields.Many2one('of.sms.account', readonly=True, string=u"Compte SMS")
    model_id = fields.Many2one('ir.model', readonly=True, string=u"Modèle")
    is_commercial = fields.Boolean(
        string=u'Est commercial',
        help=u"Indique si le texto est commercial.\n"
             u"Si oui, un message de désinscription sera ajouté à la fin du message et ne sera envoyé que du lundi au "
             u"samedi 8h-20h.\n"
             u"Note : la loi réprime pénalement le fait d'envoyer des textos non liés à l'exécution du contrat "
             u"sans ces mentions.")
    by_partner_id = fields.Many2one('res.partner', string=u"Par")
    from_mobile = fields.Char(string=u"Émetteur", readonly=True)
    to_mobile = fields.Char(string=u"Destinataire", readonly=True)
    sms_content = fields.Text(string="Contenu SMS", readonly=True)
    record_name = fields.Char(string=u"Nom de l'enregistrement", compute="_compute_record_name")
    status_string = fields.Char(string=u"Texte de réponse", readonly=True)
    status_code = fields.Selection(
        (('RECEIVED', u'Reçu'), ('failed', u'Échec envoi'), ('queued', u'Queue'), ('successful', u'Envoyé'),
         ('DELIVRD', u'Délivré'), ('EXPIRED', u'Expiré'), ('UNDELIV', u'Non délivré')),
        string=u'Statut envoi', readonly=True)
    sms_gateway_message_id = fields.Char(string=u"Passerelle SMS ID message", readonly=True)
    direction = fields.Selection((("I", "INBOUND"), ("O", "OUTBOUND")), string="Direction", readonly=True)
    message_date = fields.Datetime(
        string=u"Date envoi/réception", readonly=True,
        help=u"La date et l'heure de l'envoi et de la réception du texto.")
    media_id = fields.Binary(string=u"Média (MMS)")
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', domain=[('res_model', '=', 'of.sms.message')], string=u"Pièces-jointes MMS")

    @api.one
    @api.depends('to_mobile', 'model_id', 'record_id')
    def _compute_record_name(self):
        """Get the name of the record that this sms was sent to"""
        if self.model_id.model and self.record_id:
            my_record = self.env[self.model_id.model].search([('id', '=', self.record_id)])
            if my_record:
                if self.env['ir.model.fields'].search(
                        [('model_id.model', '=', self.model_id.model), ('name', '=', 'name')]):
                    self.record_name = my_record.name
                else:
                    self.record_name = False
            else:
                self.record_name = self.to_mobile

    # Envoyer les SMS de la file d'envoi de SMS (différé)
    # Appelée par cron
    @api.model
    def process_sms_queue(self, queue_limit):
        for queued_sms in self.search(
                [('status_code', '=', 'queued'),
                 ('message_date', '<=', datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT))],
                limit=queue_limit):
            my_sms = queued_sms.account_id.send_message(
                queued_sms.from_mobile, queued_sms.to_mobile, queued_sms.sms_content, queued_sms.model_id.model,
                queued_sms.record_id, queued_sms.media_id, queued_sms_message=queued_sms)

            # Mark it as sent to avoid it being sent again
            queued_sms.status_code = my_sms.delivery_state

            # Commit intermédiaire pour éviter le renvoi d'un SMS en cas d'erreur
            self._cr.commit()


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def get_mobile_numbers(self):
        mobile_numbers = []
        for partner in self:
            for mobile in partner.of_phone_number_ids.filtered(lambda p: p.type == '03_mobile'):
                phone_number = convert_phone_number(mobile.number, new_format='e164', strict=True)
                if phone_number:
                    mobile_numbers.append(phone_number)
                else:
                    country_code = (partner.country_id and partner.country_id.code) or \
                                   (self.env.user.company_id.country_id and
                                    self.env.user.company_id.country_id.code) or "FR"
                    for match in phonenumbers.PhoneNumberMatcher(mobile.number, country_code):
                        phone_number = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
                        mobile_numbers.append(phone_number)
        return mobile_numbers

    # Appel par l'action "Envoyer SMS" dans vue partenaires
    @api.multi
    def sms_action(self):
        default_mobile = self.env['of.sms.number'].search([])
        if default_mobile:
            default_mobile = default_mobile[0]
        else:
            raise UserError(u"Erreur ! (#ED100)\n\nAucun émetteur SMS trouvé. Les émetteurs se configurent dans le "
                            u"menu Configuration/SMS/Comptes émetteurs.")
        mobile_numbers = self.get_mobile_numbers()
        if mobile_numbers:
            return {
                'name': u'Rédaction SMS',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.sms.compose',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_from_mobile_id': default_mobile.id, 'default_to_number': ','.join(mobile_numbers),
                            'default_record_id': self.id, 'default_model': 'res.partner'}
            }
        else:
            raise UserError(u"Aucun numéro de mobile valide n'est défini pour ce partenaire !")


class CRMLead(models.Model):
    _inherit = "crm.lead"

    # Appel par l'action "Envoyer SMS" dans vue opportunités
    @api.multi
    def sms_action(self):
        self.ensure_one()
        default_mobile = self.env['of.sms.number'].search([])
        if default_mobile:
            default_mobile = default_mobile[0]
        else:
            raise UserError(u"Erreur ! (#ED100)\n\nAucun émetteur SMS trouvé. Les émetteurs se configurent dans le "
                            u"menu Configuration/SMS/Comptes émetteurs.")
        mobile_numbers = self.partner_id.get_mobile_numbers()
        if mobile_numbers:
            return {
                'name': u'Rédaction SMS',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.sms.compose',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_from_mobile_id': default_mobile.id, 'default_to_number': ','.join(mobile_numbers),
                            'default_record_id': self.id, 'default_model': 'crm.lead'}
            }
        else:
            raise UserError(u"Aucun numéro de mobile valide n'est défini pour ce partenaire !")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def sms_action(self):
        self.ensure_one()
        default_mobile = self.env['of.sms.number'].search([])
        if default_mobile:
            default_mobile = default_mobile[0]
        else:
            raise UserError(u"Erreur ! (#ED100)\n\nAucun émetteur SMS trouvé. Les émetteurs se configurent dans le "
                            u"menu Configuration/SMS/Comptes émetteurs.")
        mobile_numbers = self.partner_id.get_mobile_numbers()
        if mobile_numbers:
            return {
                'name': u'Rédaction SMS',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.sms.compose',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_from_mobile_id': default_mobile.id, 'default_to_number': ','.join(mobile_numbers),
                            'default_record_id': self.id, 'default_model': 'sale.order'}
            }
        else:
            raise UserError(u"Aucun numéro de mobile valide n'est défini pour ce client !")


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def sms_action(self):
        self.ensure_one()
        default_mobile = self.env['of.sms.number'].search([])
        if default_mobile:
            default_mobile = default_mobile[0]
        else:
            raise UserError(u"Erreur ! (#ED100)\n\nAucun émetteur SMS trouvé. Les émetteurs se configurent dans le "
                            u"menu Configuration/SMS/Comptes émetteurs.")
        mobile_numbers = self.partner_id.get_mobile_numbers()
        if mobile_numbers:
            return {
                'name': u'Rédaction SMS',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.sms.compose',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_from_mobile_id': default_mobile.id, 'default_to_number': ','.join(mobile_numbers),
                            'default_record_id': self.id, 'default_model': 'account.invoice'}
            }
        else:
            raise UserError(u"Aucun numéro de mobile valide n'est défini pour ce partenaire !")


class SMSResponse():
    delivery_state = ""
    response_string = ""
    human_read_error = ""
    mms_url = ""
    message_id = ""


class OFSmsGateway(models.Model):
    _name = "of.sms.gateway"

    name = fields.Char(required=True, string=u'Nom passerelle SMS')
    gateway_model_name = fields.Char(required='True', string=u'Nom modèle passerelle')
    can_receive_sms = fields.Boolean(string=u"Peut recevoir des messages ?")


class OFSMSGatewayOVH(models.Model):
    _name = "of.sms.gateway.ovh"
    _description = "Passerelle OVH SMS"

    name = fields.Char(required=True, string='Nom passerelle SMS', default="OVH")
    api_url = fields.Char(string='API URL', default=u"https://www.ovh.com/cgi-bin/sms/http2sms.cgi?")

    def send_message(self, sms_gateway_id, from_number, to_number, sms_content, my_model_name='', my_record_id=0,
                     media=None, queued_sms_message=None, media_filename=False, is_commercial=False):
        """Actual Sending of the sms"""

        sms_account = self.env['of.sms.account'].search([('id', '=', sms_gateway_id)])

        # Format the from number before sending
        format_from = from_number
        if u" " in format_from:
            format_from = format_from.replace(u" ", u"")
        # Format the to number before sending
        format_to = re.sub('[^+,0-9]', "", to_number)
        if u"+" in format_to:
            format_to = format_to.replace(u"+", u"00")

        if format_to:
            gateway = self.env["of.sms.gateway.ovh"].search([])[0]
            api_url = gateway.api_url
            acc_name = sms_account.account_name
            login = sms_account.account_login
            psswrd = sms_account.account_password
            if not login and not psswrd:
                raise UserError("Le compte passerelle sms n'a pas d'identifiant ni de mot de passe.")
            elif not login:
                raise UserError("Le compte passerelle sms n'a pas d'identifiant.")
            elif not psswrd:
                raise UserError("Le compte passerelle sms n'a pas de mot de passe.")

            req = api_url + u"&account=" + acc_name + u"&login=" + login + u"&password=" + psswrd\
                + u"&from=" + format_from + u"&to=" + format_to\
                + u"&message=" + urllib.quote(sms_content.encode('utf8')) + u"&contentType=text/json"
            if not is_commercial:
                req = req + u"&noStop=1"
            query_send = req.encode("utf-8")
            response = requests.get(query_send)
            response_json = response.json()
            response_string = response.text
            to_number_body = isinstance(to_number, basestring) and to_number or ','.join(to_number)
            # Réponse json en cas de succès : {"status": 100, "smsIds": [u'id_du_message']}
            # En cas d'échec : {"status": 200 (ou supérieur), "message": u"motif de l'échec"}
            # Analyse the reponse string and determine if the sms was sent successfully,
            #   otherwise return a human readable error message
            if response_json["status"] == 100:
                delivery_state = "successful"
                human_read_error = ""
                sms_gateway_message_id = response_json["smsIds"] and response_json["smsIds"][0]
                body = u"SMS envoyé au %s :<br/><br/>%s" % (to_number_body, sms_content.replace(u"\n", u"<br/>"))
                subject = u"SMS envoyé"
            else:
                delivery_state = "failed"
                human_read_error = response_json["message"]
                sms_gateway_message_id = ""
                body = u"Echec d'envoi de SMS au %s :<br/><br/>%s" % \
                       (to_number_body, sms_content.replace(u"\n", u"<br/>"))
                subject = u"Echec d'envoi de SMS: %s" % human_read_error
        else:
            delivery_state = "failed"
            human_read_error = u"Aucun numéro valide"
            response_string = u"Aucun numéro valide"
            sms_gateway_message_id = ""
            body = u"Echec d'envoi de SMS : Aucun numéro valide<br/><br/>%s" % \
                   (sms_content.replace(u"\n", u"<br/>"))
            subject = u"Echec d'envoi de SMS: %s" % human_read_error

        # Créer la notification dans le RSE
        sms_subtype = self.env['ir.model.data'].get_object('of_sms', 'of_sms_subtype')
        self.env[my_model_name].search([('id', '=', my_record_id)]).message_post(
            body=body,
            subject=subject,
            message_type="comment",
            subtype_id=sms_subtype.id,
            attachments=[])

        # Send a repsonse back saying how the sending went
        my_sms_response = SMSResponse()
        my_sms_response.delivery_state = delivery_state
        my_sms_response.response_string = response_string
        my_sms_response.human_read_error = human_read_error
        my_sms_response.message_id = sms_gateway_message_id
        return my_sms_response


class OFSmsAccount(models.Model):
    _name = "of.sms.account"
    _order = "sequence"

    name = fields.Char(string='Libellé compte', required=True)
    account_gateway_id = fields.Many2one('of.sms.gateway', string=u"Passerelle", required=True)
    gateway_model = fields.Char(string=u"Gateway Model", related="account_gateway_id.gateway_model_name")
    can_receive_sms = fields.Boolean(related="account_gateway_id.can_receive_sms")
    account_name = fields.Char(string="Nom du compte", help=u"Pour OVH, commence par sms-...")
    account_login = fields.Char(string="Identifiant")
    account_password = fields.Char(
        string="Mot de passe", default='', invisible=True, copy=False,
        help=u"Laisser vide si vous ne voulez pas que l'utilisateur puisse se connecter à la passerelle.")
    sequence = fields.Integer(string=u'Séquence', default=10)
    number_ids = fields.One2many("of.sms.number", "account_id", string=u"Comptes émetteurs")

    def send_message(self, from_number, to_number, sms_content, my_model_name='', my_record_id=0, media=None,
                     queued_sms_message=None, media_filename=None, is_commercial=False):
        """Send a message from this account"""
        return self.env[self.gateway_model].send_message(
            self.id, from_number, to_number, sms_content, my_model_name, my_record_id, media, queued_sms_message,
            media_filename=media_filename, is_commercial=is_commercial)


# Émetteur
class OFSmsNumber(models.Model):
    _name = "of.sms.number"

    name = fields.Char(string="Nom", translate=True)
    mobile_number = fields.Char(string="Sender ID", help="A mobile phone number or a 1-11 character alphanumeric name")
    account_id = fields.Many2one('of.sms.account', string="Account")


class OFSMSConfiguration(models.TransientModel):
    _name = 'of.sms.config.settings'
    _inherit = 'res.config.settings'

    alerte_interventions_equipes_veille = fields.Boolean(
        string=u"Intervenants", default=False,
        help=u"Envoyer des alertes SMS aux intervenants contenant un récapitulatif des interventions du lendemain")
    alerte_interventions_clients_veille = fields.Boolean(
        string=u"Clients d'intervention", default=False,
        help=u"Envoyer des alertes SMS aux clients contenant un récapitulatif de l'intervention du lendemain")

    @api.multi
    def set_alerte_interventions_equipes_veille(self):
        return self.env['ir.values'].sudo().set_default('of.sms.config.settings', 'alerte_interventions_equipes_veille',
                                                        self.alerte_interventions_equipes_veille)

    @api.multi
    def set_alerte_interventions_clients_veille(self):
        return self.env['ir.values'].sudo().set_default('of.sms.config.settings', 'alerte_interventions_clients_veille',
                                                        self.alerte_interventions_clients_veille)


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    of_envoye_par_sms_client = fields.Boolean(string=u"SMS client envoyé ?", default=False)

    # Appel par l'action "Envoyer SMS" dans vue planning intervention
    @api.multi
    def sms_action(self):
        self.ensure_one()
        default_mobile = self.env['of.sms.number'].search([])
        if default_mobile:
            default_mobile = default_mobile[0]
        else:
            raise UserError(u"Erreur ! (#ED100)\n\nAucun émetteur SMS trouvé. Les émetteurs se configurent dans le "
                            u"menu Configuration/SMS/Comptes émetteurs.")
        mobile_numbers = self.partner_id.get_mobile_numbers() or self.address_id.get_mobile_numbers()
        if mobile_numbers:
            return {
                'name': u'Rédaction SMS',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.sms.compose',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_from_mobile_id': default_mobile.id, 'default_to_number': ','.join(mobile_numbers),
                            'default_record_id': self.id, 'default_model': 'of.planning.intervention'}
            }
        else:
            raise UserError(u"Aucun numéro de mobile valide n'est défini pour ce partenaire !")

    # Appelé par cron journalier de rappel d'intervention
    @api.model
    def sms_notif_daily(self):

        # On récupère la date de demain (fuseau Europe/Paris) sous forme de chaîne.
        # Si on est samedi, il faut envoyer les textos de rappel du lundi,
        #   donc dans ce cas le lendemain, c'est dans 2 jours !
        maintenant = fields.datetime.now()
        date_demain_str = (fields.Datetime.context_timestamp(self, maintenant) + timedelta(days=1)).strftime(
            DEFAULT_SERVER_DATE_FORMAT)
        if maintenant.isoweekday() == 6:  # 6 est le samedi.
            date_fin_relance_str = (fields.Datetime.context_timestamp(self, maintenant) + timedelta(days=2)).strftime(
                DEFAULT_SERVER_DATE_FORMAT)
        elif maintenant.isoweekday() == 7:  # 7 est le dimanche. On n'envoie pas de texto le dimanche.
            return True
        else:
            date_fin_relance_str = date_demain_str

        intervention_obj = self.env["of.planning.intervention"].with_context(virtual_id=True)
        my_model = self.env['ir.model'].search([('model', '=', "of.planning.intervention")])

        # On récupère l'émetteur du texto
        from_number = self.env["of.sms.number"].search([])
        if not from_number:
            _logger.error(u"of_sms erreur : pas de numéro émetteur de téléphone mobile configuré.")
            return False
        from_number = from_number[0]

        # On récupère le pays "France" comme pays par défaut pour le code téléphonique (+33...) des destinataires
        #   dont le pays ne serait pas configuré.
        country_id_defaut = self.env["res.country"].search([('code', '=', 'FR')])
        if country_id_defaut:
            country_id_defaut = country_id_defaut[0]
        else:
            country_id_defaut = False

        # RAPPEL ÉQUIPE : on envoie un texto aux équipes si option activée.
        # Contrairement aux clients, pour les rendez-vous sur plusieurs jours,
        #   on envoie un texto de rappel tous les jours.
        if self.env['ir.values'].get_default('of.sms.config.settings', 'alerte_interventions_equipes_veille'):
            for employee in self.env["hr.employee"].search([]):
                message_body = u"Vos prochaines interventions :\n"
                interventions = intervention_obj.search(
                    [('employee_ids', 'in', [employee.id]),
                     ('date', '<=', date_fin_relance_str),
                     ('date_deadline', '>=', date_demain_str),
                     ('state', '=', 'confirm')],
                    order='date')
                if not interventions:
                    continue

                # On récupère les numéros de mobile des destinataires (membres équipe)
                mobile_partners_to = []
                if employee.mobile_phone:
                    # Si le pays n'est pas renseigné dans l'adresse de l'employé, on met le pays par défaut (France).
                    if not employee.address_id.country_id:
                        country_id = country_id_defaut
                    else:
                        country_id = employee.address_id.country_id
                    mobile_partners_to.append(
                        convert_phone_number(employee.mobile_phone, country_id and country_id.code or "FR"))

                # Si aucun no de portable renseigné, on passe à l'équipe suivante.
                if not mobile_partners_to:
                    continue
                mobile_partners_to_str = ','.join(mobile_partners_to)

                # On parcourt la liste des interventions.
                for intervention in interventions:
                    date = fields.Datetime.context_timestamp(intervention,
                                                             fields.Datetime.from_string(intervention.date))
                    message_body += u"%02d/%02d/%04d %02dh%02d (durée %s) : %s\n" % (
                        date.day, date.month, date.year, date.hour, date.minute, intervention.duree, intervention.name)

                # On envoie le texto.
                self.env['of.sms.message'].create({
                    'record_id': intervention.id,
                    'model_id': my_model[0].id,
                    'account_id': from_number.account_id.id,
                    'from_mobile': from_number.mobile_number,
                    'to_mobile': mobile_partners_to_str,
                    'sms_content': message_body,
                    'direction': 'O',
                    'message_date': datetime.utcnow(),
                    'status_code': 'queued',
                })

        # RAPPEL PARTICIPANT : On envoie un texto aux participants si option activée.
        if self.env['ir.values'].get_default('of.sms.config.settings', 'alerte_interventions_clients_veille'):
            # On récupère les interventions du lendemain dont le rappel n'a pas déjà été effectué.
            interventions = intervention_obj.search(
                [('date', '>=', date_demain_str),
                 ('date', '<=', date_fin_relance_str),
                 ('state', '=', 'confirm'),
                 ('of_envoye_par_sms_client', '=', False)],
                order='date')

            # On récupère le modèle de texto.
            if interventions:
                sms_template = self.env['of.sms.template'].search(
                    [('name', '=', u"Rappel automatique SMS rendez-vous client"),
                     ('model', '=', 'of.planning.intervention')])
                if not sms_template:
                    _logger.error(
                        u"of_sms rappel rdv auto erreur : pas de modèle de SMS de rappel automatique configuré.")
                    return

            for intervention in interventions:
                # On récupère le no de mobile du destinataire.
                # Si le pays n'est pas renseigné dans l'adresse du client, on met la France par défaut.
                mobile_partner_to = intervention.address_id.get_mobile_numbers()
                if not mobile_partner_to:
                    continue

                # On passe le contenu du texto par l'interpréteur Mako.
                message_body = HTMLParser().unescape(
                    self.env['mail.template'].render_template(
                        sms_template[0].template_body, sms_template[0].model_id.model, intervention.id,
                        post_process=False))

                # On envoie le texto.
                queued_sms = self.env['of.sms.message'].create({
                    'record_id': intervention.id,
                    'model_id': my_model[0].id,
                    'account_id': from_number.account_id.id,
                    'from_mobile': from_number.mobile_number,
                    'to_mobile': mobile_partner_to,
                    'sms_content': message_body,
                    'direction': 'O',
                    'message_date': datetime.utcnow(),
                    'status_code': 'queued',
                })
                # On met l'indicateur de rappel envoyé à vrai pour ne pas faire un rappel lors du prochain appel
                #   de la fonction.
                if queued_sms:
                    intervention.of_envoye_par_sms_client = True
        return True
