# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http

from odoo.addons.mail.controllers.discuss import DiscussController


class DiscussControllerDatastore(DiscussController):
    @http.route("/mail/thread/data", methods=["POST"], type="json", auth="user")
    def mail_thread_data(self, thread_model, thread_id, request_list, **kwargs):
        if thread_id >= 0:
            return super().mail_thread_data(thread_model, thread_id, request_list, **kwargs)

        # When this a datastore object, we don't have a real id, so we return a fake one
        res = {
            "hasWriteAccess": False,
            "hasReadAccess": True,
            "canPostOnReadonly": False,
        }
        if "activities" in request_list:
            res["activities"] = []
        if "attachments" in request_list:
            res["attachments"] = []
            res["mainAttachment"] = {"id": [("clear",)]}
        if "followers" in request_list:
            res["followers"] = []
        if "suggestedRecipients" in request_list:
            res["suggestedRecipients"] = []
        return res
