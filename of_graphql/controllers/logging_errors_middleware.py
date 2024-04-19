# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

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
            if typename == 'Mutation' or typename == 'Query':
                logger.info(format_log(info.context, f"{typename} on {key}"))

            return next(root, info, **args)
        except AccessError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "ACCESS_ERROR"})
        except MissingError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "MISSING_ERROR"})
        except UserError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "USER_ERROR"})
        except ValidationError as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "VALIDATION_ERROR"})
        except Exception as e:
            logger.error(
                format_log(info.context, f"Error occurred in GraphQL execution with args {args}"), exc_info=True
            )
            raise GraphQLError(e, extensions={"code": "UNKNOWN_ERROR"})
