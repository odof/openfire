# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import graphene

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.company_type import Company
from ..graphql.server_capability_query import ServerCapabilityQuery
from ..graphql.server_capability_type import ServerCapability
from ..graphql.user_mutation import UserMutation
from ..graphql.user_query import UserQuery
from ..graphql.user_type import User, UserFilterInput, UserInput

logger = logging.getLogger(__name__)


class OFGraphql(models.AbstractModel):
    """
    This model is used to register all the graphql modules installed on the database.
    It allow us to use GraphQL with a similar inheritance system as Odoo models.
    """

    _name = "of.graphql"
    _description = "OF Graphql Abstract Model"

    def _register_hook(self):
        """Registers all the graphql modules installed on the database and builds the general schema."""
        # First, clear the graphql pool for this database
        OdooGraphql.clear_pool(self.env.cr.dbname)

        # Fetch the installed modules and create the graphql schema
        # Each module that wants to add graphql should inherit from of.graphql
        # and have a method named _{module_name}_register that adds to OdooGraphql
        # what we want in Query, Mutation, Types, and Subscription
        sql = """Select name from ir_module_module where state in ('installed','to_upgrade')"""
        self.env.cr.execute(sql)
        module_list = [name for (name,) in self.env.cr.fetchall()]
        for module in module_list:
            if hasattr(self, f"_{module}_register"):
                register = getattr(self, f"_{module}_register")
                register(self.env.cr.dbname)

    def _of_graphql_register(self, dbname):
        """Loads the graphql for this module and adds it to OdooGraphql."""
        OdooGraphql.add(
            dbname,
            [
                User,
                UserInput,
                UserFilterInput,
                Company,
                UserQuery,
                UserMutation,
                ServerCapability,
                ServerCapabilityQuery,
            ],
        )

    def _add_arguments(self, new_arguments, arguments):
        """Adds new arguments to the existing arguments dictionary."""
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
        """To be overridden by other modules. Prepares the arguments for mutations."""
        return {}

    def _prepare_mutations(self, pool):
        """Fetches the arguments of installed modules and patches the mutation classes with these arguments."""
        arguments = self._prepare_arguments()

        # Patch the mutation classes with the arguments
        for mutation in pool["mutation"]:
            if mutation._name in arguments.keys():
                patch_arguments = arguments[mutation._name]
                for prop in patch_arguments.keys():
                    if hasattr(mutation, prop):
                        to_patch = getattr(mutation, prop)
                        to_patch.args.update(patch_arguments[prop])
                    else:
                        logger.error(f"Mutation {mutation} doesn't have the prop {prop}, so it cannot be patched.")

    @api.model
    def server_capabilities(self):
        """Retourne un dictionnaire des capacités du serveur
        La clé est le nom de la capacité et la valeur est un booleen indiquant si la capacité est activée."""
        return {}
