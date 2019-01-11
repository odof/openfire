# coding: utf-8

from odoo import models, fields, api
try:
    import urllib
except ImportError:
    urllib = None
import requests
from datetime import datetime
from lxml import etree
import logging
_logger = logging.getLogger(__name__)

from odoo.http import request
from odoo.exceptions import UserError

class sms_response():
     delivary_state = ""
     response_string = ""
     human_read_error = ""
     mms_url = ""
     message_id = ""

class OFSMSGatewayOVH(models.Model):
    _name = "of.sms.gateway.ovh"
    _description = "OVH SMS Gateway"

    api_url = fields.Char(string='API URL',default=u"https://www.ovh.com/cgi-bin/sms/http2sms.cgi?")

    def send_message(self, sms_gateway_id, from_number, to_number, sms_content, my_model_name='', my_record_id=0, media=None, queued_sms_message=None, media_filename=False):
        """Actual Sending of the sms"""
        sms_account = self.env['sms.account'].search([('id','=',sms_gateway_id)])

        #format the from number before sending
        format_from = from_number
        if u" " in format_from: format_from.replace(u" ", u"")
        #format the to number before sending
        format_to = to_number
        if u" " in format_to: format_to = format_to.replace(u" ", u"")
        if u"-" in format_to: format_to = format_to.replace(u"-", u"")
        if u"/" in format_to: format_to = format_to.replace(u"/", u"")
        if u"+" in format_to:
            format_to = format_to.replace(u"+", u"00") # not working properly????
        else:
            print "..."

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
        payload = {'From': format_from, 'To': format_to, 'Body': sms_content, 'StatusCallback': base_url + "/sms/ovh/receipt"}

        if queued_sms_message:
            for mms_attachment in queued_sms_message.attachment_ids:
                #For now we only support a single MMS per message but that will change in future versions
                payload['MediaUrl'] = base_url + "/web/image/" + str(mms_attachment.id) + "/media." + mms_attachment.mimetype.split("/")[1]

        if media:
            payload['MediaUrl'] = media_url

        acc_name = sms_account.ovh_account_name
        login = sms_account.ovh_login
        psswrd = sms_account.ovh_password
        req = "https://www.ovh.com/cgi-bin/sms/http2sms.cgi?&account="+acc_name+"&login="+login+"&password="+psswrd+"&from="+format_from+"&to="+format_to+"&message="+sms_content+"&contentType=text/json"
        #query_send = urllib.quote_plus(req.encode('utf8'))
        query_send = req
        response_string = requests.get(query_send)
        response_json = response_string.json()
        #response_json = {"status": 100, "smsIds": [u'153154760']}

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
        #my_sms_response.response_string = {"status":100,"smsIds":["153159302"],"creditLeft":"993.00"}
        my_sms_response.human_read_error = human_read_error
        my_sms_response.message_id = sms_gateway_message_id
        print "HAHAHAHAHAHAHAHAHAHAHAHAH\n\n\n\nHAHAHAHAHAHAHAHAHAH"
        return my_sms_response

    """def check_messages(self, account_id, message_id=""):
        " ""Checks for any new messages or if the message id is specified get only that message"" "
        sms_account = self.env['sms.account'].browse(account_id)
        
        if message_id != "":
            payload = {}
            response_string = requests.get("https://api.twilio.com/2010-04-01/Accounts/" + sms_account.twilio_account_sid + "/Messages/" + message_id, data=payload, auth=(str(sms_account.twilio_account_sid), str(sms_account.twilio_auth_token)))
        root = etree.fromstring(str(response_string.text.encode('utf-8')))
        my_messages = root.xpath('//Message')
        sms_message = my_messages[0]
        #only get the inbound ones as we track the outbound ones back to a user profile
        if sms_message.xpath('//Direction')[0].text == "inbound":
            self._add_message(sms_message, account_id)
        else:
            #get a list of all new inbound message since the last check date
            payload = {}
            if sms_account.twilio_last_check_date != False:
                my_time = datetime.strptime(sms_account.twilio_last_check_date,'%Y-%m-%d %H:%M:%S')
                payload = {'DateSent>': str(my_time.strftime('%Y-%m-%d'))}
            response_string = requests.get("https://api.twilio.com/2010-04-01/Accounts/" + sms_account.twilio_account_sid + "/Messages", data=payload, auth=(str(sms_account.twilio_account_sid), str(sms_account.twilio_auth_token)))
            root = etree.fromstring(str(response_string.text.encode('utf-8')))
            
            
            #get all pages
            messages_tag = root.xpath('//Messages')
            
            #Loop through all pages until you have reached the end
            while True:
                
                my_messages = messages_tag[0].xpath('//Message')
                for sms_message in my_messages:
                    
                    #only get the inbound ones as we track the outbound ones back to a user profile
                    if sms_message.find('Direction').text == "inbound":
                        self._add_message(sms_message, account_id)
                        
                #get the next page if there is one
                next_page_uri = messages_tag[0].attrib['nextpageuri']
                if next_page_uri != "":
                    response_string = requests.get("https://api.twilio.com" + messages_tag[0].attrib['nextpageuri'], data=payload, auth=(str(sms_account.twilio_account_sid), str(sms_account.twilio_auth_token)))
                    root = etree.fromstring(response_string.text.encode('utf-8'))
                    messages_tag = root.xpath('//Messages')
                        
                #End the loop if there are no more pages
                if next_page_uri == "":
                    break


    
        sms_account.twilio_last_check_date = datetime.utcnow()"""

    """def _add_message(self, sms_message, account_id):
        " ""Adds the new sms to the system"" "
        delivary_state = ""
        if sms_message.find('Status').text == "failed":
            delivary_state = "failed"
        elif sms_message.find('Status').text == "sent":
            delivary_state = "successful"
        elif sms_message.find('Status').text == "delivered":
            delivary_state = "DELIVRD"
        elif sms_message.find('Status').text == "undelivered":
            delivary_state = "UNDELIV"
        elif sms_message.find('Status').text == "received":
            delivary_state = "RECEIVED"
    
        my_message = self.env['sms.message'].search([('sms_gateway_message_id','=', sms_message.find('Sid').text)])
        if len(my_message) == 0 and sms_message.find('Direction').text == "inbound":
        
            target = self.env['sms.message'].find_owner_model(sms_message)
            
            twilio_gateway_id = self.env['sms.gateway'].search([('gateway_model_name', '=', 'sms.gateway.twilio')])

            discussion_subtype = self.env['ir.model.data'].get_object('mail', 'mt_comment')
            my_message = ""

            attachments = []

            _logger.error(sms_message.find('NumMedia').text)
            if sms_message.find('NumMedia').text > 0:
                sms_account = self.env['sms.account'].browse(account_id)
                
                for sub_resource in sms_message.find('SubresourceUris'):
                    media_list_url = sub_resource.text
                    _logger.error(media_list_url)
                    
                    media_response_string = requests.get("https://api.twilio.com" + media_list_url, auth=(str(sms_account.twilio_account_sid), str(sms_account.twilio_auth_token)))

                    media_root = etree.fromstring(media_response_string.text.encode('utf-8'))
                    for media_mms in media_root.xpath('//MediaList/Media'):
                        first_media_url = media_mms.find('Uri').text
                        media_filename = media_mms.find("Sid").text + ".jpg"
                        attachments.append((media_filename, requests.get("https://api.twilio.com" + first_media_url).content) )


            from_record = self.env['res.partner'].sudo().search([('mobile','=', sms_message.find('From').text)])

            if from_record:
                message_subject = "SMS Received from " + from_record.name
            else:
                message_subject = "SMS Received from " + sms_message.find('From').text
            
            if target['target_model'] == "res.partner":
                model_id = self.env['ir.model'].search([('model','=', target['target_model'])])

                my_record = self.env[target['target_model']].browse( int(target['record_id'].id) )
                my_message = my_record.message_post(body=sms_message.find('Body').text, subject=message_subject, subtype_id=discussion_subtype.id, author_id=my_record.id, message_type="comment", attachments=attachments)

                #Notify followers of this partner who are listenings to the 'discussions' subtype
                for notify_partner in self.env['mail.followers'].search([('res_model','=','res.partner'),('res_id','=',target['record_id'].id), ('subtype_ids','=',discussion_subtype.id)]):
                    my_message.needaction_partner_ids = [(4,notify_partner.partner_id.id)]

                #Create the sms record in history
                history_id = self.env['sms.message'].create({'account_id': account_id, 'status_code': "RECEIVED", 'from_mobile': sms_message.find('From').text, 'to_mobile': sms_message.find('To').text, 'sms_gateway_message_id': sms_message.find('Sid').text, 'sms_content': sms_message.find('Body').text, 'direction':'I', 'message_date':sms_message.find('DateUpdated').text, 'model_id':model_id.id, 'record_id':int(target['record_id'].id), 'by_partner_id': my_record.id})
            elif target['target_model'] == "crm.lead":
                model_id = self.env['ir.model'].search([('model','=', target['target_model'])])

                my_record = self.env[target['target_model']].browse( int(target['record_id'].id) )
                my_message = my_record.message_post(body=sms_message.find('Body').text, subject=message_subject, subtype_id=discussion_subtype.id, message_type="comment", attachments=attachments)

                #Notify followers of this lead who are listenings to the 'discussions' subtype
                for notify_partner in self.env['mail.followers'].search([('res_model','=','crm.lead'),('res_id','=',target['record_id'].id), ('subtype_ids','=',discussion_subtype.id)]):
                    my_message.needaction_partner_ids = [(4,notify_partner.partner_id.id)]

                #Create the sms record in history
                history_id = self.env['sms.message'].create({'account_id': account_id, 'status_code': "RECEIVED", 'from_mobile': sms_message.find('From').text, 'to_mobile': sms_message.find('To').text, 'sms_gateway_message_id': sms_message.find('Sid').text, 'sms_content': sms_message.find('Body').text, 'direction':'I', 'message_date':sms_message.find('DateUpdated').text, 'model_id':model_id.id, 'record_id':int(target['record_id'].id)})
            else:
                #Create the sms record in history without the model or record_id 
                history_id = self.env['sms.message'].create({'account_id': account_id, 'status_code': "RECEIVED", 'from_mobile': sms_message.find('From').text, 'to_mobile': sms_message.find('To').text, 'sms_gateway_message_id': sms_message.find('Sid').text, 'sms_content': sms_message.find('Body').text, 'direction':'I', 'message_date':sms_message.find('DateUpdated').text})
            """

    """def delivery_receipt(self, ovh_account_name, message_id):
        "" "Updates the sms message when it is successfully received by the mobile phone" ""
        my_account = self.env['sms.account'].search([('ovh_account_name','=', ovh_account_name)])[0]
        response_string = requests.get("https://api.twilio.com/2010-04-01/Accounts/" + my_account.twilio_account_sid + "/Messages/" + message_id, auth=(str(my_account.twilio_account_sid), str(my_account.twilio_auth_token)))
        root = etree.fromstring(str(response_string.text))

        #map the Twilio delivary code to the sms delivary states 
        delivary_state = ""
        if root.xpath('//Status')[0].text == "failed":
            delivary_state = "failed"
        elif root.xpath('//Status')[0].text == "sent":
            delivary_state = "successful"
        elif root.xpath('//Status')[0].text == "delivered":
            delivary_state = "DELIVRD"
        elif root.xpath('//Status')[0].text == "undelivered":
            delivary_state = "UNDELIV"

            my_message = self.env['sms.message'].search([('sms_gateway_message_id','=', message_id)])
            if len(my_message) > 0:
                my_message[0].status_code = delivary_state
                my_message[0].delivary_error_string = root.xpath('//ErrorMessage')[0].text"""

class SmsAccountOVH(models.Model):
    _inherit = "sms.account"
    _description = "Adds the OVH specfic gateway settings to the sms gateway accounts"
    _order = "sequence"

    ovh_account_name = fields.Char(string="OVH account name")
    ovh_login = fields.Char(string="OVH login")
    ovh_password = fields.Char(string="OVH password",default='', invisible=True, copy=False,
        help="Keep empty if you don't want the user to be able to connect on the system.")

    sequence = fields.Integer(string=u'Séquence', default=10)

class SmsCompose(models.Model):
    _inherit = "sms.compose"

    @api.multi
    def send_entity(self):
        """Attempt to send the sms, if any error comes back show it to the user and only log the smses that successfully sent"""
        self.ensure_one()

        gateway_model = self.from_mobile_id.account_id.account_gateway_id.gateway_model_name

        if self.delivery_time:
            #Create the queued sms
            my_model = self.env['ir.model'].search([('model','=',self.model)])
            sms_message = self.env['sms.message'].create({
                'record_id': self.record_id,
                'model_id':my_model[0].id,
                'account_id':self.from_mobile_id.account_id.id,
                'from_mobile':self.from_mobile_id.mobile_number,
                'to_mobile':self.to_number,
                'sms_content':self.sms_content,
                'status_string':'-',
                'direction':'O',
                'message_date':self.delivery_time,
                'status_code':'queued',
                'by_partner_id':self.env.user.partner_id.id,
                })

            sms_subtype = self.env['ir.model.data'].get_object('sms_frame', 'sms_subtype')
            attachments = []

            if self.media_id:
                attachments.append((self.media_filename, base64.b64decode(self.media_id)) )

            self.env[self.model].search([('id','=', self.record_id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=sms_subtype.id, attachments=attachments)

            return True
        else:
            my_sms = self.from_mobile_id.account_id.send_message(self.from_mobile_id.mobile_number, self.to_number, self.sms_content.encode('utf-8'), self.model, self.record_id, self.media_id, media_filename=self.media_filename)

        #use the human readable error message if present
        error_message = ""
        if my_sms.human_read_error != "":
            error_message = my_sms.human_read_error
        else:
            error_message = my_sms.response_string

        #display the screen with an error code if the sms/mms was not successfully sent
        if my_sms.delivary_state == "failed":
           return {
           'type':'ir.actions.act_window',
           'res_model':'sms.compose',
           'view_type':'form',
           'view_mode':'form',
           'target':'new',
           'context':{'default_to_number':self.to_number,'default_record_id':self.record_id,'default_model':self.model, 'default_error_message':error_message}
           }
        else:

            my_model = self.env['ir.model'].search([('model','=',self.model)])

            #for single smses we only record succesful sms, failed ones reopen the form with the error message
            sms_message = self.env['sms.message'].create({
                                                    'record_id': self.record_id,
                                                    'model_id':my_model[0].id,
                                                    'account_id':self.from_mobile_id.account_id.id,
                                                    'from_mobile':self.from_mobile_id.mobile_number,
                                                    'to_mobile':self.to_number,
                                                    'sms_content':self.sms_content,
                                                    'status_string':my_sms.response_string,
                                                    'direction':'O',
                                                    'message_date':datetime.utcnow(),
                                                    'status_code':my_sms.delivary_state,
                                                    'sms_gateway_message_id':my_sms.message_id,
                                                    'by_partner_id':self.env.user.partner_id.id})

            sms_subtype = self.env['ir.model.data'].get_object('sms_frame', 'sms_subtype')
            attachments = []

            if self.media_id:
                attachments.append((self.media_filename, base64.b64decode(self.media_id)) )

            self.env[self.model].search([('id','=', self.record_id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=sms_subtype.id, attachments=attachments)
