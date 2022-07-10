# -*- coding: utf-8 -*-
import time
from odoo import api, models, fields


class OFCRMActivityAction(models.TransientModel):
    _name = 'of.crm.activity.action'

    @api.model
    def default_get(self, field_list):
        result = super(OFCRMActivityAction, self).default_get(field_list)
        if self._context.get('active_model') == 'of.crm.activity' and self._context.get('active_id'):
            activity = self.env['of.crm.activity'].browse(self._context.get('active_id'))
            result['activity_id'] = activity.id
            result['date'] = activity.date or fields.Datetime.now()
        return result

    type = fields.Selection(selection=[('realize', u"Réaliser"), ('cancel', u"Annuler")], string=u"Type d'action")
    activity_id = fields.Many2one(comodel_name='of.crm.activity', string=u"Activité")
    date = fields.Datetime(string=u"Date de réalisation")
    note = fields.Text(string="Note")

    def action_message_post(self, action_type):
        # Création d'un message
        if action_type == 'done':
            title = u"Activité réalisée"
        else:
            title = u"Activité annulée"
        description = self.activity_id.description and '<p><em>%s</em></p>' % '<br/>'.join(
            self.activity_id.description.split('\n')) or ''
        note = self.note and '<p><em> => %s</em></p>' % '<br/>'.join(self.note.split('\n')) or ''
        body_html = "<div><b>%(title)s</b> : %(activity)s</div>%(description)s%(note)s" % {
            'title': title,
            'activity': self.activity_id.type_id.name,
            'description': description,
            'note': note,
        }
        if self.activity_id.opportunity_id:
            self.activity_id.opportunity_id.message_post(
                body_html, subject=self.activity_id.title, subtype_id=self.activity_id.type_id.subtype_id.id)
        if self.activity_id.order_id:
            self.activity_id.order_id.message_post(
                body_html, subject=self.activity_id.title, subtype_id=self.activity_id.type_id.subtype_id.id)

    @api.multi
    def action_realize(self):
        self.ensure_one()
        self.action_message_post('done')
        self.activity_id.write({
            'state': 'done',
            'done_date': self.date,
            'report': self.note
        })
        return True

    @api.multi
    def action_cancel(self):
        self.ensure_one()
        self.action_message_post('cancel')
        self.activity_id.write({
            'active': False,
            'state': 'canceled',
            'cancel_reason': self.note
        })
        return True
