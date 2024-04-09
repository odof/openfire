# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    of_mobile_display_planning_days_before = fields.Integer(
        string='Number of days before',
        config_parameter='of_mobile.display_planning_days_before',
    )

    of_mobile_display_planning_days_after = fields.Integer(
        string='Number of days after',
        config_parameter='of_mobile.display_planning_days_after',
    )

    of_mobile_history_limit = fields.Integer(
        string='Maximum history retrieval',
        config_parameter='of_mobile.history_limit',
    )

    of_mobile_max_size_attachment = fields.Integer(
        string='Maximum attachements size',
        config_parameter='of_mobile.max_size_attachment',
    )

    of_mobile_max_nb_attachment = fields.Integer(
        string='Maximum number of attachments',
        config_parameter='of_mobile.max_nb_attachment',
    )

    of_mobile_image_resolution_width = fields.Integer(
        string='Maximum width',
        config_parameter='of_mobile.image_resolution_width',
    )

    of_mobile_image_resolution_height = fields.Integer(
        string='Maximum height',
        config_parameter='of_mobile.image_resolution_height',
    )

    of_mobile_meeting_timesheet = fields.Selection(
        string='Time tracking mode',
        config_parameter='of_mobile.meeting_timesheet',
        selection=[
            ('no', 'No tracking'),
            ('manual', 'Manual tracking'),
            ('auto', 'Automatic tracking'),
        ],
        required=True,
    )

    of_mobile_meeting_timesheet_force = fields.Boolean(
        string='Time tracking mandatory',
        config_parameter='of_mobile.meeting_timesheet_force',
    )

    of_mobile_can_edit_days_before = fields.Integer(
        string='Number of days before can edit',
        config_parameter='of_mobile.can_edit_days_before',
    )

    of_mobile_can_edit_days_after = fields.Integer(
        string='Number of days after can edit',
        config_parameter='of_mobile.can_edit_days_after',
    )

    @api.onchange('of_mobile_display_planning_days_before')
    def _onchange_of_mobile_display_planning_days_before(self):
        if self.of_mobile_display_planning_days_before > 30:
            self.of_mobile_display_planning_days_before = 30
        if self.of_mobile_display_planning_days_before < 0:
            self.of_mobile_display_planning_days_before = 0

    @api.onchange('of_mobile_display_planning_days_after')
    def _onchange_of_mobile_display_planning_days_after(self):
        if self.of_mobile_display_planning_days_after > 60:
            self.of_mobile_display_planning_days_after = 60
        if self.of_mobile_display_planning_days_after < 0:
            self.of_mobile_display_planning_days_after = 0

    @api.onchange('of_mobile_meeting_timesheet')
    def _onchange_of_mobile_meeting_timesheet(self):
        if not self.of_mobile_meeting_timesheet or self.of_mobile_meeting_timesheet == 'no':
            self.of_mobile_meeting_timesheet_force = False

    @api.onchange('of_mobile_history_limit')
    def _onchange_of_mobile_history_limit(self):
        if self.of_mobile_history_limit > 24:
            self.of_mobile_history_limit = 24

    @api.onchange('of_mobile_can_edit_days_before')
    def _onchange_of_mobile_can_edit_days_before(self):
        if self.of_mobile_can_edit_days_before > self.of_mobile_display_planning_days_before:
            self.of_mobile_can_edit_days_before = self.of_mobile_display_planning_days_before
        if self.of_mobile_can_edit_days_before < 0:
            self.of_mobile_can_edit_days_before = 0

    @api.onchange('of_mobile_can_edit_days_after')
    def _onchange_of_mobile_can_edit_days_after(self):
        if self.of_mobile_can_edit_days_after > self.of_mobile_display_planning_days_after:
            self.of_mobile_can_edit_days_after = self.of_mobile_display_planning_days_after
        if self.of_mobile_can_edit_days_after < 0:
            self.of_mobile_can_edit_days_after = 0

    @api.onchange('of_mobile_max_size_attachment')
    def _onchange_of_mobile_max_size_attachment(self):
        if self.of_mobile_max_size_attachment > 10:
            self.of_mobile_max_size_attachment = 10

    @api.onchange('of_mobile_max_nb_attachment')
    def _onchange_of_mobile_max_nb_attachment(self):
        if self.of_mobile_max_nb_attachment > 10:
            self.of_mobile_max_nb_attachment = 10

    @api.onchange('of_mobile_image_resolution_width')
    def _onchange_of_mobile_image_resolution_width(self):
        if self.of_mobile_image_resolution_width > 1920:
            self.of_mobile_image_resolution_width = 1920

    @api.onchange('of_mobile_image_resolution_height')
    def _onchange_of_mobile_image_resolution_height(self):
        if self.of_mobile_image_resolution_height > 1920:
            self.of_mobile_image_resolution_height = 1920
