# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMActivity(models.Model):
    """CRM Activities for objects (its more like tasks)"""

    _name = 'of.crm.activity'
    _description = __doc__
    _rec_name = 'title'
    _order = 'date desc, sequence'

    sequence = fields.Integer(default=1)
    active = fields.Boolean(default=True)
    origin = fields.Selection(selection=[('opportunity', "Opportunity")], required=True, default='opportunity')
    title = fields.Char(string="Summary", required=True, tracking=True)
    opportunity_id = fields.Many2one(comodel_name='crm.lead', string="Opportunity", ondelete='cascade')
    type_id = fields.Many2one(comodel_name='mail.activity.type', string="Activity type", required=True)
    date = fields.Datetime(string="Planned date")
    deadline_date = fields.Date(string="Deadline date")
    done_date = fields.Datetime(string="Done date")
    state = fields.Selection(
        selection=[('planned', "Planned"), ('done', "Done"), ('canceled', "Cancel")],
        required=True,
        default='planned',
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users', string="Author", required=True, default=lambda self: self.env.user
    )
    vendor_id = fields.Many2one(comodel_name='res.users', string="Vendor")
    description = fields.Text()
    report = fields.Text(tracking=True)
    cancel_reason = fields.Text(tracking=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', compute='_compute_partner_id', string="Customer", store=True
    )
    phone = fields.Char(related='opportunity_id.phone', readonly=True)
    mobile = fields.Char(related='opportunity_id.mobile', readonly=True)
    email = fields.Char(related='opportunity_id.email_from', readonly=True)
    is_late = fields.Boolean(string="Late activity", compute='_compute_is_late', search='_search_is_late')
    load_attachment = fields.Boolean(string="Load an attachment")
    uploaded_attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Uploaded attachment", index=True)
    of_color_ft = fields.Char(string="Text color", compute='_compute_of_colors')
    of_color_bg = fields.Char(string="Background color", compute='_compute_of_colors')

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    def _compute_partner_id(self):
        for activity in self:
            activity.partner_id = activity.opportunity_id.partner_id

    def _compute_is_late(self):
        for activity in self:
            activity.is_late = activity.date and activity.date < fields.Datetime.now()

    def _search_is_late(self):
        return [('date', '<', fields.Datetime.now())]

    def _compute_of_colors(self):
        for activity in self:
            activity.of_color_ft = False
            activity.of_color_bg = False

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_add_attachment(self):
        raise NotImplementedError('Nope. This is only the phase 1 of migration to v16.')

    def action_button_plan(self):
        raise NotImplementedError('Nope. This is only the phase 1 of migration to v16.')

    def action_button_complete(self):
        raise NotImplementedError('Nope. This is only the phase 1 of migration to v16.')

    def action_button_cancel(self):
        raise NotImplementedError('Nope. This is only the phase 1 of migration to v16.')

    def action_button_toggle_active(self):
        for activity in self:
            activity.active = not activity.active
