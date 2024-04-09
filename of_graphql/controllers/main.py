# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

import graphdoc

from odoo import http
from odoo.http import request

from odoo.addons.graphql_base import GraphQLControllerMixin

from ..graphql.odoo_graphql import OdooGraphql

logger = logging.getLogger(__name__)


class GraphQLController(http.Controller, GraphQLControllerMixin):
    @http.route("/graphiql/openfire", auth="user")
    def graphiql(self, **kwargs):
        schema = OdooGraphql.schema(request.env.cr.dbname)
        return self._handle_graphiql_request(schema.graphql_schema)

    @http.route("/graphql/openfire", auth="user", csrf=False)
    def graphql(self, **kwargs):
        schema = OdooGraphql.schema(request.env.cr.dbname)
        return self._handle_graphql_request(schema.graphql_schema)

    @http.route("/graphql/openfire/schema", auth="user", csrf=False)
    def get_schema(self, **kwargs):
        schema = OdooGraphql.schema(request.env.cr.dbname)
        return str(schema)

    @http.route("/graphql/openfire/doc", auth="user", csrf=False)
    def get_doc(self, **kwargs):
        schema = OdooGraphql.schema(request.env.cr.dbname)
        html = graphdoc.to_doc(schema.graphql_schema)
        return html
