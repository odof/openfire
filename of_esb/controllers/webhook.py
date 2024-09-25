# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo.http import Controller, Response, request, route

logger = logging.getLogger(__name__)


class Service(Controller):
    @route('/webhook/<string:trigger>', type='http', auth="public", csrf=False)
    def webhook_execute(self, trigger, **kwargs):
        headers = {'Content-Type': 'application/json'}
        args = request.params

        request_trigger = (
            request.env['of.esb.trigger']
            .sudo()
            .search(
                [('slug_name', '=', f'/webhook/{trigger}'), ('public', '=', True), ('exec_active', '=', True)], limit=1
            )
        )
        logger.info(request_trigger)
        if request_trigger:
            # on vérifie les droits
            if user_id := request_trigger.security.authorize(args):
                # on ajoute dans les args, le user, et on envoie tout dans le bus
                args["user_id"] = user_id.id
                data = request.env['of.esb.data'].with_user(user_id.id).create({'in_data': json.dumps(args)})
                value = {'data': data.id, 'channel': trigger, 'ttype': request.env.ref('of_esb.type_webhook').id}
                bus = request.env['of.esb.bus'].with_user(user_id.id).create(value)
                data.properties = json.dumps({'uuid': bus.uuid})
                body = {'res': 'Your webhook have been queued', 'uuid': bus.uuid, 'code': 200}
                # on loggue tout ça

                data = {
                    'type': 'trigger',
                    'id': request_trigger.id,
                    'name': request_trigger.name,
                    'uuid': bus.uuid,
                    'user_id': user_id.id,
                }
                properties = {
                    'uuid': bus.uuid,
                }

                request.env['of.esb.bus'].with_user(user_id.id).send_bus(
                    ttype=request.env.ref('of_esb.type_logs'), channel='history', data=data, properties=properties
                )

            else:
                body = {'res': 'You do not have access to this webhook', 'code': 403}
        else:
            body = {'res': 'Webhook not found', 'code': 404}

        return Response(json.dumps(body), headers=headers)
