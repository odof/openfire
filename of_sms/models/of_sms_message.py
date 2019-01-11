# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)
import base64
from urllib import urlencode, quote as quote

from odoo import models, fields, api, tools

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
        autoescape=True,                # XML/HTML automatic escaping
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

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
except ImportError:
    _logger.warning("jinja2 not available, SMS templating features will not work!")

def format_tz(env, dt, tz=False, format=False):
    record_user_timestamp = env.user.sudo().with_context(tz=tz or env.user.sudo().tz or 'UTC')
    timestamp = datetime.datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)

    ts = fields.Datetime.context_timestamp(record_user_timestamp, timestamp)

    # Babel allows to format datetime in a specific language without change locale
    # So month 1 = January in English, and janvier in French
    # Be aware that the default value for format is 'medium', instead of 'short'
    #     medium:  Jan 5, 2016, 10:20:31 PM |   5 janv. 2016 22:20:31
    #     short:   1/5/16, 10:20 PM         |   5/01/16 22:20
    if env.context.get('use_babel'):
        # Formatting available here : http://babel.pocoo.org/en/latest/dates.html#date-fields
        from babel.dates import format_datetime
        return format_datetime(ts, format or 'medium', locale=env.context.get("lang") or 'en_US')

    if format:
        return ts.strftime(format)
    else:
        lang = env.context.get("lang")
        langs = env['res.lang']
        if lang:
            langs = env['res.lang'].search([("code", "=", lang)])
        format_date = langs.date_format or '%B-%d-%Y'
        format_time = langs.time_format or '%I-%M %p'

        fdate = ts.strftime(format_date).decode('utf-8')
        ftime = ts.strftime(format_time).decode('utf-8')
        return "%s %s%s" % (fdate, ftime, (' (%s)' % tz) if tz else '')

class sms_response():
     delivary_state = ""
     response_string = ""
     human_read_error = ""
     mms_url = ""
     message_id = ""

class OFSmsTemplate(models.Model):
    _name = "of.sms.template"

    name = fields.Char(required=True, string='Template Name', translate=True)
    model_id = fields.Many2one('ir.model', string='Applies to', help="The kind of document with with this template can be used")
    model = fields.Char(related="model_id.model", string='Related Document Model', store=True, readonly=True)
    template_body = fields.Text('Body', translate=True, help="Plain text version of the message (placeholders may be used here)")
    sms_from = fields.Char(string='From (Mobile)', help="Sender mobile number (placeholders may be used here). If not set, the default value will be the author's mobile number.")
    sms_to = fields.Char(string='To (Mobile)', help="To mobile number (placeholders may be used here)")
    account_gateway_id = fields.Many2one('of.sms.account', string="Account")
    model_object_field_id = fields.Many2one('ir.model.fields', string="Field", help="Select target field from the related document model.\nIf it is a relationship field you will be able to select a target field at the destination of the relationship.")
    sub_object_id = fields.Many2one('ir.model', string='Sub-model', readonly=True, help="When a relationship field is selected as first field, this field shows the document model the relationship goes to.")
    sub_model_object_field_id = fields.Many2one('ir.model.fields', string='Sub-field', help="When a relationship field is selected as first field, this field lets you select the target field within the destination document model (sub-model).")
    null_value = fields.Char(string='Default Value', help="Optional value to use if the target field is empty")
    copyvalue = fields.Char(string='Placeholder Expression', help="Final placeholder expression, to be copy-pasted in the desired template field.")
    lang = fields.Char(string='Language', help="Optional translation language (ISO code) to select when sending out an email. If not set, the english version will be used. This should usually be a placeholder expression that provides the appropriate language, e.g. ${object.partner_id.lang}.", placeholder="${object.partner_id.lang}")
    from_mobile_verified_id = fields.Many2one('of.sms.number', string="From Mobile (stored)")
    from_mobile = fields.Char(string="From Mobile", help="Placeholders are allowed here")
    media_id = fields.Binary(string="Media(MMS)")
    media_filename = fields.Char(string="Media Filename")
    media_ids = fields.Many2many('ir.attachment', string="Media(MMS)[Automated Actions Only]")

    @api.onchange('model_object_field_id')
    def _onchange_model_object_field_id(self):
        if self.model_object_field_id.relation:
            self.sub_object_id = self.env['ir.model'].search([('model','=',self.model_object_field_id.relation)])[0].id
        else:
            self.sub_object_id = False

        if self.model_object_field_id:
            self.copyvalue = self.build_expression(self.model_object_field_id.name, self.sub_model_object_field_id.name, self.null_value)

    @api.onchange('sub_model_object_field_id')
    def _onchange_sub_model_object_field_id(self):
        if self.sub_model_object_field_id:
            self.copyvalue = self.build_expression(self.model_object_field_id.name, self.sub_model_object_field_id.name, self.null_value)

    @api.onchange('from_mobile_verified_id')
    def _onchange_from_mobile_verified_id(self):
        if self.from_mobile_verified_id:
            self.from_mobile = self.from_mobile_verified_id.mobile_number

    @api.model
    def send_sms(self, template_id, record_id):
        """Send the sms using all the details in this sms template, using the specified record ID""" 
        sms_template = self.env['of.sms.template'].browse( int(template_id) )

        rendered_sms_template_body = self.env['of.sms.template'].render_template(sms_template.template_body, sms_template.model_id.model, record_id)

        rendered_sms_to = self.env['of.sms.template'].render_template(sms_template.sms_to, sms_template.model_id.model, record_id)

        gateway_model = sms_template.from_mobile_verified_id.account_id.account_gateway_id.gateway_model_name

        #Queue the SMS message since we can't directly send MMS
        queued_sms = self.env['of.sms.message'].create({
                                                    'record_id': record_id,
                                                    'model_id': sms_template.model_id.id,
                                                    'account_id':sms_template.from_mobile_verified_id.account_id.id,
                                                    'from_mobile':sms_template.from_mobile,
                                                    'to_mobile':rendered_sms_to,
                                                    'sms_content':rendered_sms_template_body,
                                                    'direction':'O',
                                                    'message_date':datetime.utcnow(),
                                                    'status_code': 'queued',
                                                    })

        #Also create the MMS attachment
        if sms_template.media_id:
            self.env['ir.attachment'].sudo().create({
                                                'name': 'mms ' + str(queued_sms.id),
                                                'type': 'binary',
                                                'datas': sms_template.media_id,
                                                'public': True,
                                                'res_model': 'sms.message',
                                                'res_id': queued_sms.id,
                                                })

        #Turn the queue manager on
        self.env['ir.model.data'].get_object('of_sms', 'sms_queue_check').active = True

    def render_template(self, template, model, res_id):
        """Render the given template text, replace mako expressions ``${expr}``
           with the result of evaluating these expressions with
           an evaluation context containing:

                * ``user``: browse_record of the current user
                * ``object``: browse_record of the document record this mail is
                              related to
                * ``context``: the context passed to the mail composition wizard

           :param str template: the template text to render
           :param str model: model name of the document record this mail is related to.
           :param int res_id: id of document records those mails are related to.
        """
        template = mako_template_env.from_string(tools.ustr(template))
        # prepare template variables
        user = self.env.user
        record = self.env[model].browse(res_id)
        variables = {
            'ctx': self._context,  # context kw would clash with mako internals
            'user': user,
            'format_tz': lambda dt, tz=False, format=False, context=self._context: format_tz(self.env, dt, tz, format),
        }
        variables['object'] = record
        try:
            render_result = template.render(variables)
        except Exception:
            _logger.error("Failed to render template %r using values %r" % (template, variables))
            render_result = u""
        if render_result == u"False":
            render_result = u""

        return render_result

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

    record_id = fields.Integer(readonly=True, string="Record")
    account_id = fields.Many2one('of.sms.account', readonly=True, string="SMS Account")
    model_id = fields.Many2one('ir.model', readonly=True, string="Model")
    by_partner_id = fields.Many2one('res.partner', string="By")
    from_mobile = fields.Char(string="From Mobile", readonly=True)
    to_mobile = fields.Char(string="To Mobile", readonly=True)
    sms_content = fields.Text(string="SMS Message", readonly=True)
    record_name = fields.Char(string="Record Name", compute="_compute_record_name")
    status_string = fields.Char(string="Response String", readonly=True)
    status_code = fields.Selection((('RECEIVED','Received'), ('failed', 'Failed to Send'), ('queued', 'Queued'), ('successful', 'Sent'), ('DELIVRD', 'Delivered'), ('EXPIRED','Timed Out'), ('UNDELIV', 'Undelivered')), string='Delivary State', readonly=True)
    sms_gateway_message_id = fields.Char(string="SMS Gateway Message ID", readonly=True)
    direction = fields.Selection((("I","INBOUND"),("O","OUTBOUND")), string="Direction", readonly=True)
    message_date = fields.Datetime(string="Send/Receive Date", readonly=True, help="The date and time the sms is received or sent")
    media_id = fields.Binary(string="Media(MMS)")
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'of.sms.message')], string="MMS Attachments")

    @api.one
    @api.depends('to_mobile', 'model_id', 'record_id')
    def _compute_record_name(self):
        """Get the name of the record that this sms was sent to"""
        if self.model_id.model != False and self.record_id:
            my_record_count = self.env[self.model_id.model].search_count([('id','=',self.record_id)])
            if my_record_count > 0:
                my_record = self.env[self.model_id.model].search([('id','=',self.record_id)])
                if self.env['ir.model.fields'].search([('model_id.model','=',self.model_id.model), ('name','=','name')]):
                    self.record_name = my_record.name
                else:
                    self.record_name = False
            else:
                self.record_name = self.to_mobile

    def find_owner_model(self, sms_message):
        """Gets the model and record this sms is meant for"""
        #look for a partner with this number
        partner_id = self.env['res.partner'].search([('mobile','=', sms_message.find('From').text )]) # using XML, used for twilio
        if len(partner_id) > 0:
            return {'record_id': partner_id[0], 'target_model': "res.partner"}
        else:
            return {'record_id': 0, 'target_model': ""}

    @api.model
    def process_sms_queue(self, queue_limit):
        #queue_limit = self.env['ir.model.data'].get_object('of_sms', 'sms_queue_check').args
        for queued_sms in self.env['of.sms.message'].search([('status_code','=','queued'), ('message_date','<=', datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT) ) ], limit=queue_limit):
            #inutile? gateway_model = queued_sms.account_id.account_gateway_id.gateway_model_name   .encode('utf-8')
            my_sms = queued_sms.account_id.send_message(queued_sms.from_mobile, queued_sms.to_mobile, queued_sms.sms_content, queued_sms.model_id.model, queued_sms.record_id, queued_sms.media_id, queued_sms_message=queued_sms)

            #Mark it as sent to avoid it being sent again
            queued_sms.status_code = my_sms.delivary_state

            #record the message in the communication log (RSE)
            self.env[queued_sms.model_id.model].browse(queued_sms.record_id).message_post(body=queued_sms.sms_content.encode('utf-8'), subject="SMS")#, subtype_id="sms_subtype")

class ResPartner(models.Model):
    _inherit = "res.partner"

    create_date_paris = fields.Datetime(string="create date in tz paris", compute="_compute_create_date_paris")#, store=True)

    @api.depends("create_date")
    def _compute_create_date_paris(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for partner in self:
            partner.create_date_paris = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.create_date))

class OFSmsCompose(models.Model):
    _name = "of.sms.compose"

    error_message = fields.Char(readonly=True)
    record_id = fields.Integer()
    model = fields.Char()
    sms_template_id = fields.Many2one('of.sms.template', string="Template")
    from_mobile_id = fields.Many2one('of.sms.number', required=True, string="From Mobile") 
    to_number = fields.Char(required=True, string='To Mobile Number', readonly=True)
    sms_content = fields.Text(string='SMS Content')
    media_id = fields.Binary(string="Media (MMS)")
    media_filename = fields.Char(string="Media Filename")
    delivery_time = fields.Datetime(string="Delivery Time")

    @api.onchange('sms_template_id')
    def _onchange_sms_template_id(self):
        """Prefills from mobile, sms_account and sms_content but allow them to manually change the content after"""
        if self.sms_template_id:
            sms_rendered_content = self.env['mail.template'].render_template(self.sms_template_id.template_body, self.sms_template_id.model_id.model, self.record_id)
            #sms_rendered_content = self.env['of.sms.template'].render_template(self.sms_template_id.template_body, self.sms_template_id.model_id.model, self.record_id)

            self.from_mobile_id = self.sms_template_id.from_mobile_verified_id.id
            self.media_id = self.sms_template_id.media_id
            self.media_filename = self.sms_template_id.media_filename
            self.sms_content = sms_rendered_content

    @api.multi
    def send_entity(self):
        """Attempt to send the sms, if any error comes back show it to the user and only log the smses that successfully sent"""
        self.ensure_one()

        gateway_model = self.from_mobile_id.account_id.account_gateway_id.gateway_model_name

        if self.delivery_time:
            #Create the queued sms
            my_model = self.env['ir.model'].search([('model','=',self.model)])
            sms_message = self.env['of.sms.message'].create({
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

            sms_subtype = self.env['ir.model.data'].get_object('of_sms', 'sms_subtype')
            attachments = []

            if self.media_id:
                attachments.append((self.media_filename, base64.b64decode(self.media_id)) )

            self.env[self.model].search([('id','=', self.record_id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=sms_subtype.id, attachments=attachments)

            return True
        else:#.encode('utf-8')
            my_sms = self.from_mobile_id.account_id.send_message(self.from_mobile_id.mobile_number, self.to_number, self.sms_content, self.model, self.record_id, self.media_id, media_filename=self.media_filename)

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
           'res_model':'of.sms.compose',
           'view_type':'form',
           'view_mode':'form',
           'target':'new',
           'context':{'default_to_number':self.to_number,'default_record_id':self.record_id,'default_model':self.model, 'default_error_message':error_message}
           }
        else:

            my_model = self.env['ir.model'].search([('model','=',self.model)])

            #for single smses we only record succesful sms, failed ones reopen the form with the error message
            sms_message = self.env['of.sms.message'].create({
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

            sms_subtype = self.env['ir.model.data'].get_object('of_sms', 'sms_subtype')
            attachments = []

            if self.media_id:
                attachments.append((self.media_filename, base64.b64decode(self.media_id)) )

            self.env[self.model].search([('id','=', self.record_id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=sms_subtype.id, attachments=attachments)

