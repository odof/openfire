# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_internal_communication = fields.Boolean(
        string="Communication Between User",
        help="If activated, allow you to send internal messages",
        implied_group='of_communication_base.group_of_internal_message',
    )

    @api.model
    def set_values(self):
        """
        Function which gives the right to see internal messages
        and which gives the admin the right to write internal messages

        Args:
            None
        Returns:
            None
        """
        super(ResConfigSettings, self).set_values()
        if self.group_internal_communication:
            admin_user = self.env.ref('base.user_admin')
            group = self.env.ref('of_communication_base.group_of_sender_internal_message')
            admin_user.write({'groups_id': [Command.link(group.id)]})
        else:
            admin_user = self.env.ref('base.user_admin')
            group = self.env.ref('of_communication_base.group_of_sender_internal_message')
            admin_user.write({'groups_id': [Command.unlink(group.id)]})
