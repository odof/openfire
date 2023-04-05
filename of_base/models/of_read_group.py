# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.models import VALID_AGGREGATE_FUNCTIONS, regex_field_agg
from odoo.tools import OrderedSet

_logger = logging.getLogger(__name__)


class OfReadGroup(models.AbstractModel):
    """
    Cette classe permet d'effectuer un read_group sur un champ qui ne serait normalement pas accepté par Odoo.
    Normalement, un read_group ne peut être effectué que sur un champ ayant le paramètre store=True.
    Une classe héritant de of.readgroup peut en plus autoriser cette fonction sur les champs ayant le paramètre
    of_custom_groupby.
    Il faut ensuite surcharger _read_group_process_groupby afin de modifier la query et de retourner les
    éléments nécessaire à son interprétation.
    """

    _name = 'of.readgroup'

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        self.check_access_rights('read')
        query = self._where_calc(domain)
        fields = fields or [f.name for f in self._fields.values() if f.store]

        groupby = [groupby] if isinstance(groupby, str) else list(OrderedSet(groupby))
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(gb, query) for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(query, 'read')
        for gb in groupby_fields:
            if gb not in self._fields:
                raise UserError(_("Unknown field %r in 'groupby'", gb))
            if not self._fields[gb].base_field.groupable:
                raise UserError(
                    _(
                        "Field %s is not a stored field, only stored fields (regular or "
                        "many2many) are valid for the 'groupby' parameter",
                        self._fields[gb],
                    )
                )
            # Modification OpenFire : Un champ custom peut ne pas être présent en base de données
            gb_field = self._fields[gb].base_field
            if not getattr(gb_field, 'of_custom_groupby', False):
                assert gb_field.store and gb_field.column_type, (
                    "Fields in 'groupby' must be regular "
                    "database-persisted fields (no function or related fields), or function fields with store=True"
                )
            # Fin modification OpenFire

        aggregated_fields = []
        select_terms = []
        fnames = []  # list of fields to flush

        for fspec in fields:
            if fspec == 'sequence':
                continue
            if fspec == '__count':
                # the web client sometimes adds this pseudo-field in the list
                continue

            match = regex_field_agg.match(fspec)
            if not match:
                raise UserError(_("Invalid field specification %r.", fspec))

            name, func, fname = match.groups()
            if func:
                # we have either 'name:func' or 'name:func(fname)'
                fname = fname or name
                field = self._fields.get(fname)
                if not field:
                    raise ValueError("Invalid field %r on model %r" % (fname, self._name))
                if not (field.base_field.store and field.base_field.column_type):
                    raise UserError(_("Cannot aggregate field %r.", fname))
                if func not in VALID_AGGREGATE_FUNCTIONS:
                    raise UserError(_("Invalid aggregation function %r.", func))
            else:
                # we have 'name', retrieve the aggregator on the field
                field = self._fields.get(name)
                if not field:
                    raise ValueError("Invalid field %r on model %r" % (name, self._name))
                if not (field.base_field.store and field.base_field.column_type and field.group_operator):
                    continue
                func, fname = field.group_operator, name

            fnames.append(fname)

            if fname in groupby_fields:
                continue
            if name in aggregated_fields:
                raise UserError(_("Output name %r is used twice.", name))
            aggregated_fields.append(name)

            expr = self._inherits_join_calc(self._table, fname, query)
            if func.lower() == 'count_distinct':
                term = 'COUNT(DISTINCT %s) AS "%s"' % (expr, name)
            else:
                term = '%s(%s) AS "%s"' % (func, expr, name)
            select_terms.append(term)

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        self._flush_search(domain, fields=fnames + groupby_fields)

        groupby_terms, orderby_terms = self._read_group_prepare(order, aggregated_fields, annotated_groupbys, query)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not self._context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''  # noqa: E731
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''  # noqa: E731

        query = """
            SELECT min("%(table)s".id) AS id, count("%(table)s".id) AS "%(count_field)s" %(extra_fields)s
            FROM %(from)s
            %(where)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }
        self._cr.execute(query, where_clause_params)
        fetched_data = self._cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        # # Modif OpenFire : Recherche directe du nom par name_get sur l'objet ciblé
        # #  (la méthode standart Odoo procédait par lecture du champ sur l'objet courant,
        # #   ce qui est impossible dans le cadre d'un champ one2many)
        # for gb in annotated_groupbys:
        #     if gb['type'] == 'many2one':
        #         gb_field = gb['field']
        #         rel = self._fields[gb_field].base_field.comodel_name
        #         gb_obj = self.env[rel]
        #         gb_ids = [r[gb_field] for r in fetched_data if r[gb_field]]
        #         gb_dict = {d[0]: d for d in gb_obj.browse(gb_ids).name_get()}
        #         for d in fetched_data:
        #             d[gb_field] = gb_dict.get(d[gb_field], False)
        # # Fin modif OpenFire

        self._read_group_resolve_many2x_fields(fetched_data, annotated_groupbys)

        data = [{k: self._read_group_prepare_data(k, v, groupby_dict) for k, v in r.items()} for r in fetched_data]

        fill_temporal = self.env.context.get('fill_temporal')
        if (data and fill_temporal) or isinstance(fill_temporal, dict):
            # fill_temporal = {} is equivalent to fill_temporal = True
            # if fill_temporal is a dictionary and there is no data, there is a chance that we
            # want to display empty columns anyway, so we should apply the fill_temporal logic
            if not isinstance(fill_temporal, dict):
                fill_temporal = {}
            data = self._read_group_fill_temporal(data, groupby, aggregated_fields, annotated_groupbys, **fill_temporal)

        result = [self._read_group_format_result(d, annotated_groupbys, groupby, domain) for d in data]

        if lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            result = self._read_group_fill_results(
                domain,
                groupby_fields[0],
                groupby[len(annotated_groupbys) :],
                aggregated_fields,
                count_field,
                result,
                read_group_order=order,
            )
        return result

    def _field_create(self):
        """
        Ajoute la mise à jour de of_custom_groupby dans la table ir_model_fields
        """
        super(OfReadGroup, self)._field_create()
        cr = self._cr
        query = "UPDATE ir_model_fields SET of_custom_groupby=%s WHERE model=%s AND name=%s"
        for field in self._fields.itervalues():
            cr.execute(query, (getattr(field, 'of_custom_groupby', False), self._name, field.name))

    @api.model
    def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        """
        Fonction identique à la fonction définie dans models.py, à l'exception de la zone spécifiée.
        Permet d'ordonner les résultats d'une requête en fonction de champs avec of_custom_groupby=True.
        Nécessite que la fonction of_custom_groupby_generate_order soit surchargée pour chacun de ces champs.
        """
        if seen is None:
            seen = set()
        self._check_qorder(order_spec)

        order_by_elements = []
        for order_part in order_spec.split(','):
            order_split = order_part.strip().split(' ')
            order_field = order_split[0].strip()
            order_direction = order_split[1].strip().upper() if len(order_split) == 2 else ''
            if reverse_direction:
                order_direction = 'ASC' if order_direction == 'DESC' else 'DESC'
            do_reverse = order_direction == 'DESC'

            field = self._fields.get(order_field)
            if not field:
                raise ValueError(_("Sorting field %s not found on model %s") % (order_field, self._name))

            if order_field == 'id':
                order_by_elements.append('"%s"."%s" %s' % (alias, order_field, order_direction))
            else:
                if field.inherited:
                    field = field.base_field
                if field.store and field.type == 'many2one':
                    key = (field.model_name, field.comodel_name, order_field)
                    if key not in seen:
                        seen.add(key)
                        order_by_elements += self._generate_m2o_order_by(alias, order_field, query, do_reverse, seen)
                elif field.store and field.column_type:
                    qualifield_name = self._inherits_join_calc(alias, order_field, query, implicit=False, outer=True)
                    if field.type == 'boolean':
                        qualifield_name = f"COALESCE({qualifield_name}, false)"
                    order_by_elements.append(f"{qualifield_name} {order_direction}")
                # OF Modification OpenFire
                elif getattr(field, 'of_custom_groupby', False):
                    key = (field.model_name, field.comodel_name, order_field)
                    if key not in seen:
                        seen.add(key)
                        order_by_elements += self.of_custom_groupby_generate_order(
                            alias, order_field, query, do_reverse, seen
                        )
                # Fin modification OpenFire
                else:
                    _logger.warning("Model %r cannot be sorted on field %r (not a column)", self._name, order_field)
                    continue  # ignore non-readable or "non-joinable" fields

        return order_by_elements

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, do_reverse, seen):
        """
        Fonction à surcharger pour ajouter des jointures dans query et retourner un ordre de tri.
        Le format de retour est le même que celui de _generate_order_by_inner()
        """
        return []
