# -*- coding: utf-8 -*-

import logging
import json

from odoo import http, tools, fields
from odoo.http import request
from odoo.addons.of_web_api.models.of_web_api import MAGIC_AUTH_FIELDS

_logger = logging.getLogger(__name__)


class OFAPIWeb(http.Controller):
    u"""
Fonctions de l'API :
    - création d'enregistrements
    """

    def login(self, body):
        login = body.get('login')
        if not login:
            return {
                'code': 400,
                'message': u"Missing login",
            }
        password = body.get('password')
        if not password:
            return {
                'code': 400,
                'message': u"Missing password",
            }
        user_id = request.session.authenticate(request.db, login, password)
        if not user_id:
            return {
                'code': 401,
                'message': u"Impossible to login. Please verify the login and password",
            }
        return {
            'code': 200,
            'message': u"OK",
        }

    @http.route(['/api/creation'], methods=['POST'], type='json', auth="none", csrf=False)
    def api_creation(self, **kw):
        body = request.jsonrequest
        login_response = self.login(body)
        if login_response.get('code') != 200:
            _logger.warning(u"OF ERROR api creation : %s" % login_response.get('message', u""))
            return login_response
        model_name = body.get('model')
        if not model_name:
            _logger.warning(u"OF ERROR api creation : missing model")
            return {
                'code': 400,
                'message': u"Missing model",
            }
        model = request.env['ir.model'].search([('model', '=', model_name)])
        # le modèle n'existe pas
        if not model:
            _logger.warning(u"OF ERROR api creation : model not found in database")
            return {
                'code': 400,
                'message': u"Model not found in database",
            }
        # l'accès à ce modèle est interdit'
        if not model.of_api_auth:
            _logger.warning(
                u"OF ERROR api creation : OpenFire API is not authorized to access this model (%s)." % model.model)
            return {
                'code': 400,
                'message': u"OpenFire API is not authorized to access this model (%s)." % model.model,
            }
        vals = body.get('values')
        if isinstance(vals, basestring):
            vals = json.loads(vals)
        authorized_fields = request.env['ir.model.fields'].search(
            [('model_id', '=', model.id), ('of_api_auth', '=', True), ('name', 'not in', MAGIC_AUTH_FIELDS)])
        authorized_fields_name = authorized_fields.mapped('name')
        # Restreindre les valeurs de création aux champs autorisés
        vals_clean = {k: vals[k] for k in authorized_fields_name if k in vals}
        try:
            record = self.create_record(model_name, vals_clean)
        except Exception as e:
            _logger.warning(u"OF ERROR api creation : impossible to create record\n%s\n" % e)
            return {
                'code': 400,
                'message': u"Impossible to create record",
            }
        return {
            'code': 200,
            'message': u"Record with id %d was succesfully created : %s" % (record.id, record.name),
        }

    def create_record(self, model_name, vals):
        u"""Fonction dissociée pour héritage"""
        of_api_user_id = request.env.ref('of_web_api.of_api_user').id
        return request.env[model_name].sudo(of_api_user_id).create(vals)
