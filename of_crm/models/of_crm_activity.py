# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import pytz
from datetime import timedelta
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from odoo.addons.of_utils.models.of_utils import get_selection_label


class OFCRMActivity(models.Model):
    _name = 'of.crm.activity'
    _inherit = ['mail.thread']
    _description = "OF Activité de CRM/Ventes"
    _rec_name = 'title'
    _order = 'date desc, sequence'

    @api.model_cr_context
    def _auto_init(self):
        """
        On récupère les prochaines activités programmées
        """
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % (self._table,))
        exists = bool(cr.fetchall())
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_crm')])
        migrate_activities = module_self and module_self.latest_version < '10.0.1.1.0' or False
        cr.execute("SELECT * FROM of_sale_activity")
        current_activies = cr.dictfetchall()
        order_ids = map(lambda x: x['order_id'], current_activies)
        res = super(OFCRMActivity, self)._auto_init()
        if not exists:
            tz = pytz.timezone('Europe/Paris')
            opportunities = self.env['crm.lead'].search([('next_activity_id', '!=', False)])
            for opportunity in opportunities:
                self.create({'opportunity_id': opportunity.id,
                             'title': opportunity.next_activity_id.name,
                             'type_id': opportunity.next_activity_id.id,
                             'date': tz.localize(
                                 fields.Datetime.from_string(
                                     (opportunity.date_action or fields.Date.today()) + ' 09:00:00')
                             ).astimezone(pytz.utc),
                             'description': opportunity.title_action,
                             'user_id': SUPERUSER_ID,
                             'vendor_id': opportunity.user_id and opportunity.user_id.id or SUPERUSER_ID,
                             'state': 'planned'})
        if exists and migrate_activities and current_activies:
            # insert the activities linked to the Sale in their table
            for activity in current_activies:
                active = True
                state = activity['state']
                if state == 'cancelled':
                    active = False
                    state = 'canceled'
                cr.execute(
                    'INSERT INTO "of_crm_activity" ("create_uid", "uploaded_attachment_id", "type_id", '
                    '"user_id", "vendor_id", "description", "deadline_date", "sequence", "order_id", '
                    '"title", "write_uid", "state", "write_date", "report", "create_date", "load_attachment", '
                    '"origin", "active") VALUES '
                    '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);',
                    (
                        activity['create_uid'], activity['uploaded_attachment_id'], activity['activity_id'],
                        activity['create_uid'], activity['user_id'], activity['description'],
                        activity['date_deadline'] or None, activity['sequence'], activity['order_id'],
                        activity['summary'] or None, activity['write_uid'], state, activity['write_date'] or None,
                        activity['report'] or None, activity['create_date'] or None, activity['load_attachment'],
                        'sale_order', active
                    )
                )
            # recompute follow-up fields
            orders = self.env['sale.order'].browse(order_ids)
            orders._compute_of_activities_state()
        return res

    sequence = fields.Integer(string='Sequence', default=1)
    active = fields.Boolean(string='Actif', default=True)
    origin = fields.Selection(selection='_get_selection_origin', string='Origin', required=True, default='opportunity')
    title = fields.Char(string=u"Résumé", required=True, track_visibility="always")
    order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order', ondelete='cascade')
    opportunity_id = fields.Many2one(comodel_name='crm.lead', string=u"Opportunité", ondelete='cascade')
    type_id = fields.Many2one(comodel_name='crm.activity', string="Activity type", required=True)
    date = fields.Datetime(string='Planned date')
    deadline_date = fields.Date(string='Deadline date')
    done_date = fields.Datetime(string='Done date')
    state = fields.Selection(
        selection=[('planned', u"Planifiée"),
                   ('done', u"Réalisée"),
                   ('canceled', u"Annulée")], string=u"État", required=True, default='planned',
        track_visibility="onchange")
    user_id = fields.Many2one(
        comodel_name='res.users', string=u"Auteur", required=True, default=lambda self: self.env.user)
    vendor_id = fields.Many2one(comodel_name='res.users', string=u"Commercial")
    description = fields.Text(string=u"Description")
    report = fields.Text(string=u"Compte-rendu", track_visibility="onchange")
    cancel_reason = fields.Text(string=u"Raison d'annulation", track_visibility="onchange")
    partner_id = fields.Many2one(related='opportunity_id.partner_id', string=u"Client", readonly=True)
    phone = fields.Char(related='opportunity_id.phone', string=u"Téléphone", readonly=True)
    mobile = fields.Char(related='opportunity_id.mobile', string=u"Mobile", readonly=True)
    email = fields.Char(related='opportunity_id.email_from', string=u"Courriel", readonly=True)
    is_late = fields.Boolean(string=u"Activité en retard", compute="_compute_is_late", search="_search_is_late")
    load_attachment = fields.Boolean(string='Load an attachment')
    uploaded_attachment_id = fields.Many2one(comodel_name='ir.attachment', string='Uploaded attachment')
    # Couleurs
    of_color_ft = fields.Char(string=u"Couleur de texte", compute='_compute_custom_colors')
    of_color_bg = fields.Char(string=u"Couleur de fond", compute='_compute_custom_colors')

    @api.multi
    def _compute_is_late(self):
        now = fields.Datetime.now()
        today = fields.Date.today()
        for activity in self:
            if activity.origin == 'opportunity':
                activity.is_late = \
                    activity.state == 'planned' and activity.date < now if activity.date else False
            else:  # == 'sale_order'
                activity.is_late = \
                    activity.state == 'planned' and activity.deadline_date < today if activity.deadline_date else False

    @api.model
    def _search_is_late(self, operator, value):
        late_activities = self.env['of.crm.activity'].search(
            [('state', '=', 'planned'),
             '|',
             '&', ('origin', '=', 'opportunity'), ('date', '<', fields.Datetime.now()),
             '&', ('origin', '=', 'sale_order'), ('deadline_date', '<', fields.Date.today())])
        if operator == '=':
            return [('id', 'in', late_activities.ids)]
        else:
            return [('id', 'not in', late_activities.ids)]

    @api.onchange('opportunity_id')
    def _onchange_opportunity_id(self):
        if self.opportunity_id:
            self.vendor_id = self.opportunity_id.user_id

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            if self.origin == 'opportunity':
                user_id = self.type_id.of_user_id.id
                self.deadline_date = self._of_get_crm_activity_date_deadline()
            else:  # == 'sale_order'
                order_obj = self.env['sale.order']
                user_id = order_obj._of_get_sale_activity_user_id(self.order_id, self.type_id)
                self.deadline_date = order_obj._of_get_sale_activity_date_deadline(self.order_id, self.type_id)
            self.title = self.type_id.of_short_name
            self.description = self.type_id.description
            self.load_attachment = self.type_id.of_load_attachment
            if user_id:
                self.vendor_id = user_id

    @api.multi
    def _compute_custom_colors(self):
        for activity in self:
            if activity.vendor_id:
                activity.of_color_ft = activity.vendor_id.of_color_ft
                activity.of_color_bg = activity.vendor_id.of_color_bg
            else:
                activity.of_color_ft = "#0D0D0D"
                activity.of_color_bg = "#F0F0F0"

    @api.multi
    def _of_get_crm_activity_date_deadline(self):
        self.ensure_one()

        if not self.type_id:
            return False

        compute_date = self.type_id.of_compute_date
        days = self.type_id.days
        field_name = {
            'project_date': 'of_date_projet',
            'decision_date': 'date_deadline'
        }
        crm_field = field_name.get(compute_date)
        if crm_field:
            ddate = getattr(self.opportunity_id, crm_field)
            ddate = fields.Date.from_string(ddate)
        else:
            ddate = fields.Date.from_string(fields.Date.today())
        if ddate:
            delta = timedelta(days=days)
            return ddate + delta
        return False

    @api.model
    def _get_selection_origin(self):
        return [
            ('opportunity', _('Opportunity')),
            ('sale_order', _('Sale Order'))
        ]

    @api.multi
    def message_track(self, tracked_fields, initial_values):
        return super(OFCRMActivity, self.with_context(to_lead=True)).message_track(tracked_fields, initial_values)

    @api.multi
    def message_post(self, body='', subject=None, message_type='notification',
                     subtype=None, parent_id=False, attachments=None,
                     content_subtype='html', **kwargs):
        self.ensure_one()
        if self.opportunity_id and self._context.get("to_lead"):
            self.opportunity_id.message_post(body=body, subject=subject, message_type=message_type,
                                             subtype=subtype, parent_id=parent_id, attachments=attachments,
                                             content_subtype=content_subtype, **kwargs)
        return super(OFCRMActivity, self).message_post(body=body, subject=subject, message_type=message_type,
                                                       subtype=subtype, parent_id=parent_id, attachments=attachments,
                                                       content_subtype=content_subtype, **kwargs)

    @api.multi
    def action_plan(self):
        self.write({'state': 'planned'})
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def action_complete(self):
        current_states = {rec: get_selection_label(self, rec._name, 'state', rec.state) for rec in self}
        for rec in self:
            if rec.load_attachment and rec.type_id.of_mandatory and not rec.uploaded_attachment_id:
                raise ValidationError(_('An attachment is required to complete the activity'))
        self.write({
            'state': 'done',
            'done_date': fields.Datetime.now()
        })
        self._post_order_message_status(current_states)
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def action_cancel(self):
        current_states = {rec: get_selection_label(self, rec._name, 'state', rec.state) for rec in self}
        self.write({
            'state': 'canceled',
            'active': False
        })
        self._post_order_message_status(current_states)
        if self._context.get('close_and_reload'):  # only from the SaleOrder Form view
            return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.multi
    def _post_order_message_status(self, current_states):
        for rec in self:
            if rec.order_id:
                to_state = get_selection_label(self, rec._name, 'state', rec.state)
                rec.order_id.message_post(
                    body=_("Activity status change %s : %s -> %s") % (rec.title, current_states[rec], to_state))

    @api.multi
    def action_add_attachment(self):
        self.ensure_one()
        context = self._context.copy()
        context['default_activity_id'] = self.id
        if self.origin == 'opportunity':
            context['default_lead_id'] = self.opportunity_id.id
        else:
            context['default_order_id'] = self.order_id.id
        view_id = self.env.ref(
            'of_crm.of_add_attachment_activity_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'of.add.attachment.activity',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': context
        }
