# -*- coding: utf-8 -*-
#import logging
#_logger = logging.getLogger(__name__)
from odoo import api, fields, models

class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    sms_template_id = fields.Many2one('of.sms.template',string="SMS Template")

    @api.model
    def _get_states(self):
        res = super(IrActionsServer, self)._get_states()
        res.insert(0, ('sms', 'Send SMS'))
        return res

    @api.model
    def run_action_sms(self, action, eval_context=None):
        if not action.sms_template_id:
            return False
        self.env['of.sms.template'].send_sms(action.sms_template_id.id, self.env.context.get('active_id'))
        return False

class IrAttachmentSMS(models.Model):
    _inherit = "ir.attachment"

    mms = fields.Boolean(string="MMS")

class ResPartnerSms(models.Model):
    _inherit = "res.partner"

    @api.multi
    def sms_action(self):
        self.ensure_one()
        default_mobile = self.env['of.sms.number'].search([])[0]
        return {
            'name': 'SMS Compose',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.sms.compose',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_from_mobile_id': default_mobile.id,'default_to_number':self.mobile, 'default_record_id':self.id,'default_model':'res.partner'}
         }

    @api.onchange('country_id','mobile')
    def _onchange_mobile(self):
        """Tries to convert a local number to e.164 format based on the partners country, don't change if already in e164 format"""
        if self.mobile:

            if self.country_id and self.country_id.phone_code:
                if self.mobile.startswith("0"):
                    self.mobile = "+" + str(self.country_id.phone_code) + self.mobile[1:].replace(" ","")
                elif self.mobile.startswith("+"):
                    self.mobile = self.mobile.replace(" ","")
                else:
                    self.mobile = "+" + str(self.country_id.phone_code) + self.mobile.replace(" ","")
            else:
                self.mobile = self.mobile.replace(" ","")

class ResCountrySms(models.Model):
    _inherit = "res.country"

    mobile_prefix = fields.Char(string="Mobile Prefix")

class CRMLead(models.Model):
    _inherit = "crm.lead"

    @api.multi
    def sms_action(self):
        self.ensure_one()
        default_mobile = self.env['of.sms.number'].search([])[0]
        return {
            'name': 'SMS Compose',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.sms.compose',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_from_mobile_id': default_mobile.id,'default_to_number':self.mobile, 'default_record_id':self.id,'default_model':'crm.lead'}
         }
