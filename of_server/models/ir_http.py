# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import os

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils

from odoo.addons.base.ir.ir_http import IrHttp
from odoo.http import request

# DÉBUT MODIFICATION OPENFIRE
# Génération de logs pour le débogage temps d'exécution
import time
of_id = 1
# FIN MODIFICATION OPENFIRE

_logger = logging.getLogger(__name__)

UID_PLACEHOLDER = object()


@classmethod
def _dispatch(cls):
    # locate the controller method
    try:
        rule, arguments = cls._find_handler(return_rule=True)
        func = rule.endpoint
    except werkzeug.exceptions.NotFound, e:
        return cls._handle_exception(e)

    # check authentication level
    try:
        auth_method = cls._authenticate(func.routing["auth"])
    except Exception as e:
        return cls._handle_exception(e)

    processing = cls._postprocess_args(arguments, rule)
    if processing:
        return processing

    # set and execute handler
    try:
        request.set_handler(func, arguments, auth_method)
        # DÉBUT MODIFICATION OPENFIRE
        # Génération de logs pour le débogage temps d'exécution
        global of_id
        of_base_url = request.httprequest.base_url
        if of_base_url.find("/longpolling/poll") != -1:
            longpolling = True
        else:
            longpolling = False
            of_id += 1
            of_compteur = of_id
            of_debut = time.time()
            of_params = request.params
            if len(str(of_params)) > 4096:
                of_params = str(of_params)[:4096] + " [...]"
            _logger.info(
                u"OF DEBOGUE DEBUT %s %s - UID %s - appel %s",
                os.getpid(),
                of_compteur,
                request.env.uid,
                of_base_url,
            )
        try:
            result = request.dispatch()
        finally:
            if not longpolling:
                of_temps = time.time() - of_debut
                if of_temps >= 90:
                    signe = 9
                else:
                    signe = int(of_temps / 10)
                if signe == 0:
                    # Opération rapide, on ne met pas les paramètres pour alléger les logs.
                    _logger.info(
                        u"OF DEBOGUE FIN" + str(signe) + u" %s %s - UID %s - Temps : %ss - appel %s",
                        os.getpid(),
                        of_compteur,
                        request.env.uid,
                        of_temps,
                        of_base_url,
                    )
                else:
                    _logger.info(
                        u"OF DEBOGUE FIN" + str(signe) + u" %s %s- UID %s - Temps : %ss  - appel %s %s",
                        os.getpid(),
                        of_compteur,
                        request.env.uid,
                        of_temps,
                        of_base_url,
                        of_params,
                    )
        # FIN MODIFICATION OPENFIRE
        if isinstance(result, Exception):
            raise result
    except Exception, e:
        return cls._handle_exception(e)

    return result

IrHttp._dispatch = _dispatch
