# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, fields, models


class ESBConnection(models.Model):
    _name = "of.esb.connection"
    _description = "ESB Connection"

    name = fields.Char()
    ttype = fields.Selection(selection=[], string="Type")
    security = fields.Many2one(comodel_name="of.esb.security")
    is_valid = fields.Boolean()

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_button_test_connection(self):
        if self.connect():
            self.is_valid = True
            return self._send_notification_message(message=_("Connection Test Successful!"), ttype="success")
        self.is_valid = False
        return self._send_notification_message(message=_("Connection Test Unsuccessful!"), ttype="error")

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def connect(self):
        if hasattr(self, f"connect_{self.ttype}"):
            return getattr(self, f"connect_{self.ttype}")()

        return False

    def get_out_example(self):
        if hasattr(self, f"get_out_example_{self.ttype}"):
            return getattr(self, f"get_out_example_{self.ttype}")()
        return False

    def get_in_example(self):
        if hasattr(self, f"get_in_example_{self.ttype}"):
            return getattr(self, f"get_in_example_{self.ttype}")()
        return False

    def _send_notification_message(self, message, ttype):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": ttype, "sticky": False},
        }
