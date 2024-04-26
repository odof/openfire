# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import logging

import graphdoc

from odoo import http
from odoo.http import Response, request

from ..graphql.odoo_graphql import OdooGraphql
from .graphql_controller_mixin import GraphQLControllerMixin

logger = logging.getLogger(__name__)


class GraphQLController(http.Controller, GraphQLControllerMixin):
    @http.route("/graphiql/openfire", auth="user")
    def graphiql(self, **kwargs):
        request.env['of.graphql']._prepare_mutations(OdooGraphql.get_pool(request.env.cr.dbname))
        OdooGraphql.debug(request.env.cr.dbname)
        schema = OdooGraphql.schema(request.env.cr.dbname)
        return self._handle_graphiql_request(schema.graphql_schema)

    @http.route("/graphql/openfire", auth="public", csrf=False)
    def graphql(self, **kwargs):
        # ici, pour que sur le mobile ce soit plus simple, on ne met pas de auth=user, on teste juste si
        # l'authentification est faite et sinon, on retourne un code ressemblant à celui de json-rpc
        if not request.session.uid:
            headers = {'Content-Type': 'application/json'}
            body = {
                "error": {
                    "code": 100,
                    "message": "Odoo Session Expired",
                    "data": {
                        "name": "odoo.http.SessionExpiredException",
                    },
                }
            }

            return Response(json.dumps(body), headers=headers)

        request.env['of.graphql']._prepare_mutations(OdooGraphql.get_pool(request.env.cr.dbname))

        schema = OdooGraphql.schema(request.env.cr.dbname)
        return self._handle_graphql_request(schema.graphql_schema)

    @http.route("/graphql/openfire/schema", auth="user", csrf=False)
    def get_schema(self, **kwargs):
        request.env['of.graphql']._prepare_mutations(OdooGraphql.get_pool(request.env.cr.dbname))

        schema = OdooGraphql.schema(request.env.cr.dbname)
        return str(schema)

    @http.route("/graphql/openfire/doc", auth="user", csrf=False)
    def get_doc(self, **kwargs):
        request.env['of.graphql']._prepare_mutations(OdooGraphql.get_pool(request.env.cr.dbname))

        schema = OdooGraphql.schema(request.env.cr.dbname)
        html = graphdoc.to_doc(schema.graphql_schema)
        return html
