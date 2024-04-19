# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import odoo
from odoo import http
from odoo.http import request


class ControllersOfMobile(http.Controller):
    """
    Controller permettant l'authentification de l'application mobile
    """

    @http.route(['/api/v1/user/login'], methods=['POST'], type='json', auth="public", csrf=False)
    def login(self):
        """
        Fonction de login legacy. Elle est utilisée pour que l'app mobile
        puisse choisir de soit se connecter sur une v10
        ou une v16 de manière transparente
        """
        body = request.get_json_data()

        username = body.get('username', False)
        password = body.get('password', False)
        if not password or not username:
            return {'code': 400, 'message': 'Missing username or password', 'session_id': None}
        user_id = request.session.authenticate(request.db, username, password)

        if not user_id:
            return {'code': 401, 'message': 'Impossible to login.', 'session_id': None}
        if request.env.user.of_user_type == 'inactive':
            return {'code': 303, 'message': 'Impossible to login.', 'session_id': None}

        request.session.db = request.db

        registry = odoo.modules.registry.Registry(request.db)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, request.session.uid, request.session.context)
            # request._save_session would not update the session_token
            # as it lacks an environment, rotating the session myself
            http.root.session_store.rotate(request.session, env)
            request.future_response.set_cookie(
                'session_id', request.session.sid, max_age=http.SESSION_LIFETIME, httponly=True
            )
            return {'code': 200, 'message': 'Logged in', 'server_version': '16.0', 'session_id': request.session.sid}

    @http.route(['/api/v1/attachments/<attachmentId>'], methods=['POST'], type='json', auth="user")
    def attachment_get(self, **args):
        attachment_id = int(args.get('attachmentId', False))
        if not attachment_id:
            return {'code': 400, 'message': "Value id is missing from body.", 'session_id': None}
        attachment = request.env['ir.attachment'].sudo().search([('id', '=', attachment_id)])
        if not attachment:
            return {'code': 404, 'message': "No image found with id %s." % attachment_id, 'session_id': None}
        return {
            'code': 200,
            'message': 'Ok',
            'data': attachment.datas,
        }
