# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class Attachment(OdooObjectType):
    _name = 'Attachment'
    _type = 'types'

    of_intervention_report = graphene.Boolean(name='interventionReport')


class AttachmentInput(graphene.InputObjectType):
    _name = "AttachmentInput"
    _type = 'types'

    of_intervention_report = graphene.Boolean(name='interventionReport')
