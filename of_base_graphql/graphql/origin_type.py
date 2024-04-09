# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene


class Origin(graphene.Enum):
    WEB = 'web'
    MOBILE = 'mobile'
