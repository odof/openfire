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

        request_trigger = request.env['esb.trigger'].search([('slug_name', '=', trigger), ('public', '=', True)])

        if request_trigger:
            # on vérifie les droits
            if user_id := request_trigger.security.authorize(args):
                # on ajoute dans les args, le user, et on envoie tout dans le bus
                args['user_id'] = user_id
                data = self.env['esb.data'].create({'in_data': args})
                value = {'data': data.id, 'channel': trigger, 'ttype': 'webhook'}
                bus = self.env['esb.bus'].create(value)
                body = {'res': 'Your webhook have been queued', 'uuid': bus.uuid, 'code': 200}
            else:
                body = {'res': 'You do not have access to this webhook', 'code': 200}
        else:
            body = {'res': 'Webhook not found', 'code': 404}

        return Response(json.dumps(body), headers=headers)
