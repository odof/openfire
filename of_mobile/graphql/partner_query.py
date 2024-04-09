# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.osv import expression

from odoo.addons.of_base.models.res_partner import convert_phone_number
from odoo.addons.of_base_graphql.graphql.partner_type import Partner

from .partner_type import PartnerCheckDuplications


class PartnerQuery(graphene.ObjectType):
    _name = 'PartnerQuery'
    _type = 'query'

    search_partners = graphene.List(
        graphene.NonNull(Partner),
        required=True,
        query=graphene.String(),
        filter_on_companies=graphene.Boolean(),
        description="Recherche des partners sur le champ nom, ref, email ou numéro de téléphone",
    )

    refresh_partners = graphene.List(
        graphene.NonNull(Partner),
        required=True,
        retrieve_ids=graphene.List(
            graphene.NonNull(graphene.Int),
            description="Liste des ids à récupérer obligatoirement",
        ),
        updated_since_ids=graphene.List(
            graphene.NonNull(graphene.Int),
            description="Liste des partners à retourner s'ils ont été mis à jour depuis la dernière synchronisation",
        ),
        updated_since=graphene.DateTime(
            description="Date de la dernière synchronisation",
        ),
    )

    partner_check_duplications = graphene.Boolean(
        required=True,
        query=graphene.Argument(PartnerCheckDuplications),
    )

    @staticmethod
    def resolve_search_partners(root, info, query, filter_on_companies=False):
        env = info.context['env']
        domain = [
            '|',
            '|',
            '|',
            ['name', 'ilike', query],
            ['ref', '=', query],
            ['email', 'ilike', query],
            ['of_phone_number_ids.number', 'ilike', query],
        ]
        if filter_on_companies:
            domain = expression.AND([domain, [('is_company', '=', True)]])

        return env['res.partner'].search(domain, limit=10) or []

    @staticmethod
    def resolve_refresh_partners(root, info, retrieve_ids=None, updated_since_ids=None, updated_since=None):
        if retrieve_ids is None:
            retrieve_ids = []
        if updated_since_ids is None:
            updated_since_ids = []
        env = info.context['env']
        domain = []

        if updated_since and updated_since_ids:
            domain = expression.AND([domain, [('write_date', '>', updated_since)]])
            domain = expression.AND([domain, [('id', 'in', updated_since_ids)]])

        if retrieve_ids:
            domain = expression.OR([domain, [('id', 'in', retrieve_ids)]])

        return env['res.partner'].sudo().search(domain) if domain else []

    @staticmethod
    def resolve_partner_check_duplications(root, info, query):
        env = info.context['env']
        if query.email and env['res.partner'].sudo().search([('email', '=', query.email)]):
            return True

        if query.phone_numbers:
            user = env.user
            default_country = user.country_id or user.company_id.country_id
            default_country_code = default_country and default_country.code or 'FR'

            phone_numbers_normalized = [convert_phone_number(n, default_country_code) for n in query.phone_numbers]

            if (
                env['of.res.partner.phone']
                .sudo()
                .search([('number', 'in', phone_numbers_normalized)])
                .mapped('partner_id')
            ):
                return True
        return False
