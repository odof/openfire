# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.company_type import Company
from ..graphql.user_mutation import UserMutation
from ..graphql.user_query import UserQuery
from ..graphql.user_type import User, UserFilterInput

logger = logging.getLogger(__name__)


class OFGraphql(models.AbstractModel):
    _name = 'of.graphql'

    def _register_hook(self):
        """Ici, on va lancer tous les register des modules graphql odoo pour construire le schéma général"""
        # D'abord on vide le pool graphql sur cette base là
        OdooGraphql.clear_pool(self.env.cr.dbname)

        # on va chercher les modules installés et on crée le schéma graphql
        # chaque module qui veut ajouter du graphql, doit faire un héritage de of.graphql
        # et avoir une méthode dont le nom est _{nom du module}_register qui va ajouter dans OdooGraphql
        # ce que l'on veut en Query, Mutation, Types et Subscription
        sql = """Select name from ir_module_module where state in ('installed','to_upgrade')"""
        self.env.cr.execute(sql)
        module_list = [name for (name,) in self.env.cr.fetchall()]
        for module in module_list:
            if hasattr(self, f"_{module}_register"):
                register = getattr(self, f"_{module}_register")
                register(self.env.cr.dbname)

    def _of_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                User,
                UserFilterInput,
                Company,
                UserQuery,
                UserMutation,
            ],
        )
