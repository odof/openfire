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

        request_trigger = request.env['esb.trigger'].sudo().search([('slug_name', '=', trigger), ('public', '=', True)])

        if request_trigger:
            # on vérifie les droits
            if user_id := request_trigger.security.authorize(args):
                # on ajoute dans les args, le user, et on envoie tout dans le bus
                args["user_id"] = user_id.id
                data = request.env['esb.data'].sudo().create({'in_data': json.dumps(args)})
                value = {'data': data.id, 'channel': trigger, 'ttype': request.env.ref('of_esb.type_webhook').id}
                bus = request.env['esb.bus'].sudo().create(value)
                body = {'res': 'Your webhook have been queued', 'uuid': bus.uuid, 'code': 200}
                # on loggue tout ça
                data_value = {
                    'in_data': json.dumps({'type': 'trigger', 'id': request_trigger.id, 'name': request_trigger.name}),
                    'properties': json.dumps({'uuid': bus.uuid}),
                }
                data = request.env['esb.data'].create(data_value)
                bus_value = {
                    'channel': 'history',
                    'ttype': request.env.ref('of_esb.type_logs').id,
                    'data': data.id,
                }
                request.env['esb.bus'].create(bus_value)

            else:
                body = {'res': 'You do not have access to this webhook', 'code': 200}
        else:
            body = {'res': 'Webhook not found', 'code': 404}

        return Response(json.dumps(body), headers=headers)
