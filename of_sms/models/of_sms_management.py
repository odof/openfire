# -*- coding: utf-8 -*-

try:
    import urllib
except ImportError:
    urllib = None
import requests

if urllib:
    from urllib import urlencode

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from lxml import etree
import logging
_logger = logging.getLogger(__name__)
import re
from odoo import models, fields, api
from odoo.http import request
from odoo.exceptions import UserError

class sms_response():
     delivary_state = ""
     response_string = ""
     human_read_error = ""
     mms_url = ""
     message_id = ""

class OFSmsGateway(models.Model):
    _name = "of.sms.gateway"

    name = fields.Char(required=True, string='Gateway Name')
    gateway_model_name = fields.Char(required='True', string='Gateway Model Name')
    can_receive_sms = fields.Boolean(string="Can receive messages?")

class OFSMSGatewayOVH(models.Model):
    _name = "of.sms.gateway.ovh"
    _description = "OVH SMS Gateway"

    api_url = fields.Char(string='API URL',default=u"https://www.ovh.com/cgi-bin/sms/http2sms.cgi?")

    def send_message(self, sms_gateway_id, from_number, to_number, sms_content, my_model_name='', my_record_id=0, media=None, queued_sms_message=None, media_filename=False):
        """Actual Sending of the sms"""
        sms_account = self.env['of.sms.account'].search([('id','=',sms_gateway_id)])

        #format the from number before sending
        format_from = from_number
        if u" " in format_from: format_from = format_from.replace(u" ", u"")
        #format the to number before sending
        format_to = re.sub('[^\+0-9]',"",to_number)
        if u"+" in format_to: format_to = format_to.replace(u"+", u"00")

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        media_url = ""

        #Create an attachment for the mms now since we need a url now
        if media:
            attachment_id = self.env['ir.attachment'].sudo().create({
                                                                'name': 'mms ' + str(my_record_id),
                                                                'type': 'binary', 'datas': media,
                                                                'public': True,
                                                                'mms': True,
                                                                'datas_fname': media_filename
                                                                })

            #Force the creation of the new attachment before you make the request
            request.env.cr.commit()
    
            if media_filename:
                media_url = base_url + "/sms/ovh/mms/" + str(attachment_id.id) + "/" + media_filename
            else:
                media_url = base_url + "/sms/ovh/mms/" + str(attachment_id.id) + "/media." + attachment_id.mimetype.split("/")[1]

        #send the sms/mms
        #payload = {'From': format_from, 'To': format_to, 'Body': sms_content, 'StatusCallback': base_url + "/sms/ovh/receipt"}

        """if queued_sms_message:
            for mms_attachment in queued_sms_message.attachment_ids:
                #For now we only support a single MMS per message but that will change in future versions
                payload['MediaUrl'] = base_url + "/web/image/" + str(mms_attachment.id) + "/media." + mms_attachment.mimetype.split("/")[1]

        if media:
            payload['MediaUrl'] = media_url"""

        gateway = self.env["of.sms.gateway.ovh"].search([])[0]
        api_url = gateway.api_url#.decode("utf-8")#.strip("https://")#.encode('utf-8')
        acc_name = sms_account.account_name#.encode('utf-8')
        login = sms_account.account_login
        psswrd = sms_account.account_password#.encode('utf-8')
        req = api_url + u"&account="+acc_name+u"&login="+login+u"&password="+psswrd+u"&from="+format_from+u"&to="+format_to+u"&message="+sms_content+u"&contentType=text/json"

        #query_send = urllib.quote_plus(req.encode("utf-8")).replace('%3A', ':').replace('%2F', '/')
        #req = urlencode(req)
        query_send = req.encode("utf-8")
        response_string = requests.get(query_send)
        response_json = response_string.json()
        #response_json = {"status": 100, "smsIds": [u'153154760']}
        #response_json = {"status": 200, "message": u"NAPAMARCHÉ"}

        #Analyse the reponse string and determine if it sent successfully other wise return a human readable error message   
        if response_json["status"] == 100:
            delivary_state = "successful"
            human_read_error = ""
            sms_gateway_message_id = response_json["smsIds"] and response_json["smsIds"][0]
        else:
            delivary_state = "failed"
            human_read_error = response_json["message"]
            sms_gateway_message_id = ""

        #send a repsonse back saying how the sending went
        my_sms_response = sms_response()
        my_sms_response.delivary_state = delivary_state
        my_sms_response.response_string = response_string.text
        #my_sms_response.response_string = {"status": 100, "smsIds": [u'153154760']}
        my_sms_response.human_read_error = human_read_error
        my_sms_response.message_id = sms_gateway_message_id
        #print "HAHAHAHAHAHAHAHAHAHAHAHAH\n\n\n\nHAHAHAHAHAHAHAHAHAH"
        return my_sms_response

class OFSmsAccount(models.Model):
    _name = "of.sms.account"
    _order = "sequence"

    name = fields.Char(string='Account Name', required=True)
    account_gateway_id = fields.Many2one('of.sms.gateway', string="Account Gateway", required=True)
    gateway_model = fields.Char(string="Gateway Model", related="account_gateway_id.gateway_model_name")
    can_receive_sms = fields.Boolean(related="account_gateway_id.can_receive_sms")
    account_name = fields.Char(string="Account name")
    account_login = fields.Char(string="Account login")
    account_password = fields.Char(string="Account password",default='', invisible=True, copy=False,
        help="Keep empty if you don't want the user to be able to connect on the system.")
    sequence = fields.Integer(string=u'Sequence', default=10)
    number_ids = fields.One2many("of.sms.number","account_id",string="Sender numbers")

    def send_message(self, from_number, to_number, sms_content, my_model_name='', my_record_id=0, media=None, queued_sms_message=None, media_filename=None):
        """Send a message from this account"""
        return self.env[self.gateway_model].send_message(self.id, from_number, to_number, sms_content, my_model_name, my_record_id, media, queued_sms_message, media_filename=media_filename)

    @api.model
    def check_all_messages(self):
        """Check for any messages that might have been missed during server downtime"""
        my_accounts = self.env['of.sms.account'].search([])
        for sms_account in my_accounts:
            if sms_account.can_receive_sms:
                self.env[sms_account.account_gateway_id.gateway_model_name].check_messages(sms_account.id)

class OFSmsNumber(models.Model):
    _name = "of.sms.number"

    name = fields.Char(string="Name", translate=True)
    mobile_number = fields.Char(string="Sender ID", help="A mobile phone number or a 1-11 character alphanumeric name")
    account_id = fields.Many2one('of.sms.account', string="Account")

"""class OFAlarm(models.Model):
    _name = "of.alarm"
    _description = 'Alarm'

    @api.depends('interval', 'duration')
    def _compute_duration_minutes(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_minutes = alarm.duration
            elif alarm.interval == "hours":
                alarm.duration_minutes = alarm.duration * 60
            elif alarm.interval == "days":
                alarm.duration_minutes = alarm.duration * 60 * 24
            else:
                alarm.duration_minutes = 0

    _interval_selection = {'minutes': 'Minute(s)', 'hours': 'Hour(s)', 'days': 'Day(s)'}

    name = fields.Char(string=u"Name", required=True)
    type = fields.Selection([
                    (u'sms', u"SMS"),
                    (u'notif', u"Notification (À implémenter)"),
                    (u'email', u"EMail (À implémenter)"),
                    ], string="Alarm type", default=u"sms")
    duration = fields.Integer('Amount', required=True, default=1)
    interval = fields.Selection(list(_interval_selection.iteritems()), 'Unit', required=True, default='hours')
    duration_minutes = fields.Integer('Duration in minutes', compute='_compute_duration_minutes', store=True, help="Duration in minutes")"""

class OFSMSConfiguration(models.TransientModel):
    _name = 'of.sms.config.settings'
    _inherit = 'res.config.settings'

    alerte_interventions_equipes_veille = fields.Boolean(string=u"Équipes d'intervention", default=False,
        help=u"Envoyer des alertes SMS aux équipes d'interventions contenant un récapitulatif des interventions du lendemain")
    alerte_interventions_clients_veille = fields.Boolean(string=u"Clients d'intervention", default=False,
        help=u"Envoyer des alertes SMS aux clients contenant un récapitulatif de l'intervention du lendemain")

    @api.multi
    def set_alerte_interventions_equipes_veille(self):
        return self.env['ir.values'].sudo().set_default('of.sms.config.settings', 'alerte_interventions_equipes_veille', self.alerte_interventions_equipes_veille)

    @api.multi
    def set_alerte_interventions_clients_veille(self):
        return self.env['ir.values'].sudo().set_default('of.sms.config.settings', 'alerte_interventions_clients_veille', self.alerte_interventions_clients_veille)

