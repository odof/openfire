# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from graphql import GraphQLError

from odoo.exceptions import AccessError, MissingError, UserError, ValidationError

from .format_log import format_log

logger = logging.getLogger(__name__)


class LoggingErrorsMiddleware:
    def resolve(self, next, root, info, **args):
        try:
            typename = info.path.typename
            key = info.path.key

            # Filtre des logs sur les Query et les Mutations
            if typename in ['Mutation', 'Query']:
                logger.info(format_log(info.context, f"{typename} on {key}"))

            return next(root, info, **args)
        except AccessError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "ACCESS_ERROR"}) from e
        except MissingError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "MISSING_ERROR"}) from e
        except ValidationError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "VALIDATION_ERROR"}) from e
        except UserError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "USER_ERROR"}) from e
        except Exception as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "UNKNOWN_ERROR"}) from e
