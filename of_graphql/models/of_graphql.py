# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import graphene

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.company_type import Company
from ..graphql.user_mutation import UserMutation
from ..graphql.user_query import UserQuery
from ..graphql.user_type import User, UserFilterInput, UserInput

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
                UserInput,
                UserFilterInput,
                Company,
                UserQuery,
                UserMutation,
            ],
        )

    def _add_arguments(self, new_arguments, arguments):
        for mutation in new_arguments.keys():
            if mutation in arguments.keys():
                for prop in arguments[mutation].keys():
                    for new_prop in new_arguments[mutation].keys():
                        if prop == new_prop:
                            for arg in new_arguments[mutation][new_prop].keys():
                                arguments[mutation][prop][arg] = graphene.Argument(
                                    new_arguments[mutation][new_prop][arg]
                                )
            else:
                arguments[mutation] = {}
                for new_prop in new_arguments[mutation].keys():
                    arguments[mutation][new_prop] = {}
                    for arg in new_arguments[mutation][new_prop].keys():
                        arguments[mutation][new_prop][arg] = graphene.Argument(new_arguments[mutation][new_prop][arg])
        return arguments

    def _prepare_arguments(self):
        # To be super by other module
        return {}

    def _prepare_mutations(self, pool):
        # on va chercher tous les arguments des modules installés
        arguments = self._prepare_arguments()

        # on patch les classes mutations avec ces arguments
        for mutation in pool['mutation']:
            if mutation._name in arguments.keys():
                patch_arguments = arguments[mutation._name]
                for prop in patch_arguments.keys():
                    if hasattr(mutation, prop):
                        to_patch = getattr(mutation, prop)
                        to_patch.args.update(patch_arguments[prop])
                    else:
                        logger.error(
                            f"La mutation {mutation} n'a pas la prop {prop}, elle ne peut donc pas être patchée"
                        )
