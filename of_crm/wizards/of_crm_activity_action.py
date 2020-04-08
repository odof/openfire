# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OFCRMActivityAction(models.TransientModel):
    _name = 'of.crm.activity.action'

    @api.model
    def default_get(self, fields):
        result = super(OFCRMActivityAction, self).default_get(fields)
        if self._context.get('active_model') == 'of.crm.activity' and self._context.get('active_id'):
            activity = self.env['of.crm.activity'].browse(self._context.get('active_id'))
            result['activity_id'] = activity.id
            result['date'] = activity.date
        return result

    type = fields.Selection(selection=[('realize', u"Réaliser"), ('cancel', u"Annuler")], string=u"Type d'action")
    activity_id = fields.Many2one(comodel_name='of.crm.activity', string=u"Activité")
    date = fields.Datetime(string=u"Date de réalisation")
    note = fields.Text(string="Note", required=True)

    @api.multi
    def action_realize(self):
        self.ensure_one()
        # Création d'un message
        body_html = "<div><b>%(title)s</b> : %(activity)s</div>%(description)s%(report)s" % {
            'title': u"Activité réalisée",
            'activity': self.activity_id.type_id.name,
            'description': self.activity_id.description and '<p><em>%s</em></p>' % '<br/>'.join(self.activity_id.description.split('\n')) or '',
            'report': "<p><em> => %s</em></p>" % '<br/>'.join(self.note.split('\n')),
        }
        self.activity_id.opportunity_id.message_post(
            body_html, subject=self.activity_id.title, subtype_id=self.activity_id.type_id.subtype_id.id)
        self.activity_id.write({'state': 'realized', 'date': self.date, 'report': self.note})
        return True

    @api.multi
    def action_cancel(self):
        self.ensure_one()
        # Création d'un message
        body_html = "<div><b>%(title)s</b> : %(activity)s</div>%(description)s%(cancel_reason)s" % {
            'title': u"Activité annulée",
            'activity': self.activity_id.type_id.name,
            'description': self.activity_id.description and '<p><em>%s</em></p>' % '<br/>'.join(self.activity_id.description.split('\n')) or '',
            'cancel_reason': "<p><em> => %s</em></p>" % '<br/>'.join(self.note.split('\n')),
        }
        self.activity_id.opportunity_id.message_post(
            body_html, subject=self.activity_id.title, subtype_id=self.activity_id.type_id.subtype_id.id)
        self.activity_id.write({'state': 'canceled', 'cancel_reason': self.note})
        return True

