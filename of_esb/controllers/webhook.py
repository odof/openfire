# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo.http import Controller, Response, request, route


class Service(Controller):
    @route("/webhook/<string:trigger>", type="http", auth="public", csrf=False)
    def webhook_execute(self, trigger, **kwargs):
        """
        Executes a webhook based on the provided trigger and additional arguments.

        Args:
            trigger (str): The trigger identifier for the webhook.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A JSON response indicating the result of the webhook execution.
        """
        headers = {"Content-Type": "application/json"}
        args = request.params
        if json_data := request.httprequest.get_data() and request.get_json_data():
            args.update(json_data)

        request_trigger = (
            request.env["of.esb.trigger"]
            .sudo()
            .search(
                [("slug_name", "=", f"/webhook/{trigger}"), ("public", "=", True), ("exec_active", "=", True)], limit=1
            )
        )
        if not request_trigger:
            return Response(json.dumps({"res": "Webhook not found", "code": 404}), headers=headers)

        # check if the user is authorized to execute the webhook
        if user_id := request_trigger.security.authorize(args):
            # adds the user to the args, and sends everything to the bus
            args["user_id"] = user_id.id
            data = request.env["of.esb.data"].with_user(user_id.id).create({"in_data": json.dumps(args)})
            value = {"data": data.id, "channel": trigger, "ttype": request.env.ref("of_esb.type_webhook").id}
            bus = request.env["of.esb.bus"].with_user(user_id.id).create(value)
            data.properties = json.dumps({"uuid": bus.uuid})

            body = {"res": "Your webhook have been queued", "uuid": bus.uuid, "code": 200}

            # logs webhook execution
            data = {
                "type": "trigger",
                "id": request_trigger.id,
                "name": request_trigger.name,
                "uuid": bus.uuid,
                "user_id": user_id.id,
            }
            properties = {
                "uuid": bus.uuid,
            }
            request.env["of.esb.bus"].with_user(user_id.id).send_bus(
                ttype=request.env.ref("of_esb.type_logs"), channel="history", data=data, properties=properties
            )

        else:
            body = {"res": "You do not have access to this webhook", "code": 403}

        return Response(json.dumps(body), headers=headers)
