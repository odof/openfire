# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _


class CRMActivity(models.Model):
    _inherit = 'crm.activity'

    @api.model_cr_context
    def _auto_init(self):
        """
        Init the new field 'of_short_name' for the existing activities and set the column as "not null"
        """
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.columns "
                   "WHERE table_name = 'crm_activity' AND column_name = 'of_short_name'")
        exists = bool(cr.fetchall())
        res = super(CRMActivity, self)._auto_init()
        if not exists:
            cr.execute(
                "UPDATE crm_activity "
                "SET of_short_name = MMS.name "
                "FROM mail_message_subtype MMS "
                "WHERE subtype_id = MMS.id AND of_short_name IS NULL")
            # Cause of existing crm.activities we have to apply the constraint manually
            cr.execute("ALTER TABLE crm_activity ALTER of_short_name SET NOT NULL;")
        return res

    days = fields.Integer(string='Delay')  # change the standard string
    of_user_id = fields.Many2one(comodel_name='res.users', string="Assigned to", index=True)
    of_short_name = fields.Char(string='Short Name', required=True)
    of_object = fields.Selection(selection='_get_of_object_selection', string='Object')
    of_compute_date = fields.Selection(
        selection='_of_get_selection_compute_date', compute='_compute_of_compute_date', string='Compute Date',
        store=True)
    of_compute_date_crm = fields.Selection(selection='_get_of_compute_date_selection_crm', string='Compute Date')
    of_compute_date_sale = fields.Selection(selection='_get_of_compute_date_selection_sale', string='Compute Date')
    of_compute_date_both = fields.Selection(selection='_get_of_compute_date_selection_both', string='Compute Date')
    of_automatic_recompute = fields.Boolean(string='Automatic recompute', default=True)
    of_mandatory = fields.Boolean(
        string='Mandatory', help="Prevent the confirmation of an order if the activity is not carried out")
    of_load_attachment = fields.Boolean(string='Load an attachment')

    @api.onchange('team_id')
    def _onchange_team_id(self):
        domain = {'of_user_id': False}
        if not self.team_id:
            self.of_user_id = False
        if self.team_id and self.team_id.member_ids:
            user_ids = self.team_id.member_ids.ids
            domain['of_user_id'] = "[('id', 'in', %s)]" % user_ids
        return {
            'domain': domain
        }

    @api.onchange('of_compute_date')
    def _onchange_of_compute_date(self):
        self.of_automatic_recompute = self.of_compute_date not in ['today_date', False] and \
            self.of_object == 'sale_order'

    @api.multi
    @api.depends('of_object', 'of_compute_date_crm', 'of_compute_date_sale', 'of_compute_date_both')
    def _compute_of_compute_date(self):
        for rec in self:
            if rec.of_object == 'opportunity':
                rec.of_compute_date = rec.of_compute_date_crm
            elif rec.of_object == 'sale_order':
                rec.of_compute_date = rec.of_compute_date_sale
            else:
                rec.of_compute_date = rec.of_compute_date_both

    @api.model
    def _get_of_compute_date_selection_sale(self):
        return [
            ('confirmation_date', _('Customer Order confirmation date')),
            ('today_date', _('Date of the day')),
            ('reference_install_date', _('Reference installation date')),
            ('estimated_install_date', _('Estimated installation date')),
            ('technical_visit_date', _('Technical visit date'))
        ]

    @api.model
    def _get_of_compute_date_selection_crm(self):
        return [
            ('today_date', _('Date of the day')),
            ('project_date', _('Project date')),
            ('decision_date', _('Decision date'))
        ]

    @api.model
    def _get_of_compute_date_selection_both(self):
        return [
            ('today_date', _('Date of the day'))
        ]

    @api.model
    def _of_get_selection_compute_date(self):
        return self._get_of_compute_date_selection_sale() + self._get_of_compute_date_selection_crm()

    @api.model
    def _get_of_object_selection(self):
        return [
            ('opportunity', _('Opportunity')),
            ('sale_order', _('Sale Order'))
        ]
