# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools.misc import OrderedSet, unique


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_planning_data(
        self,
        domain,
        groupby,
        read_specification,
        limit=None,
        offset=0,
    ):
        """
        Returns the result of a read_group (and optionally search for and read records inside each
        group), and the total number of groups matching the search domain.

        :param domain: search domain
        :param groupby: list of field to group on (see ``groupby``` param of ``read_group``)
        :param read_specification: web_read specification to read records within the groups
        :param limit: see ``limit`` param of ``read_group``
        :param offset: see ``offset`` param of ``read_group``
        :return: {
            'groups': [
                {
                    '<groupby_1>': <value_groupby_1>,
                    ...,
                    '__record_ids': [<ids>]
                }
            ],
            'records': [<record data>]
            'length': total number of groups
        }
        """
        # TODO: group_expand doesn't currently respect the limit/offset
        lazy = not limit and not offset and len(groupby) == 1
        # Because there is no limit by group, we can fetch record_ids as aggregate
        final_result = self.web_read_group(
            domain,
            ['__record_ids:array_agg(id)'],
            groupby,
            limit=limit,
            offset=offset,
            lazy=lazy,
        )
        all_record_ids = self._planning_get_all_record_ids(final_result)
        all_records, final_result['records'] = self._planning_get_all_records(all_record_ids, read_specification)

        # Add other groups for which there is no record
        self._planning_add_empty_records(final_result, groupby)

        # Update groups with record_ids
        self._planning_update_groups(all_records, final_result, groupby, lazy)
        return final_result

    def _planning_get_all_record_ids(self, final_result):
        """Get all record ids from the result of a read_group"""
        return tuple(
            unique(record_id for one_group in final_result['groups'] for record_id in one_group['__record_ids'])
        )

    def _transform_all_records(self, all_records):
        """Transform records to be able to use them in the PlanningView (made records's M2O object friendly)"""
        all_records_transformed = []
        for record in all_records:
            record_new = dict(record)
            for key, value in record_new.items():
                if key.endswith('_id') and isinstance(value, tuple) and len(value) == 2:
                    record_new[key] = {'id': value[0], 'display_name': value[1]}
            all_records_transformed.append(record_new)
        return all_records_transformed

    def _planning_get_all_records(self, all_record_ids, read_specification):
        """Get all records and read them"""
        # Do search_fetch to order records (model order can be no-trivial)
        # FIXME : specific function available in master (Odoo 17 and above)
        # all_records = self.search_fetch([('id', 'in', all_record_ids)], read_specification.keys())
        # final_result['records'] = all_records.web_read(read_specification)
        all_records = self.search([('id', 'in', all_record_ids)])
        all_records_values = all_records.read(read_specification)
        # Transform records to be able to use them in the PlanningView (made records's M2O object friendly)
        all_records_transformed = self._transform_all_records(all_records_values)
        return all_records, all_records_transformed

    def _planning_update_groups(self, all_records, final_result, groupby, lazy):
        """Update groups to sort keys and remove useless keys"""
        ordered_set_ids = OrderedSet(all_records._ids)
        keys_to_delete = ['__domain', f'{groupby[0]}_count' if lazy else '__count', '__fold']
        for group in final_result['groups']:
            group['__record_ids'] = list(ordered_set_ids & OrderedSet(group['__record_ids']))
            for key in keys_to_delete:
                group.pop(key, None)

    def _planning_add_empty_records(self, final_result, groupby):
        """Add empty records for groups without record.
        That allows to display empty rows for Resource that have no record in the view.
        """
        res_ids = [group[groupby[0]] for group in final_result['groups']]
        res_ids = list(map(lambda x: x and x[0], res_ids))
        field_id = self.env['ir.model.fields'].sudo().search([('name', '=', groupby[0]), ('model_id', '=', self._name)])
        domain = self._planning_add_empty_records_domain(res_ids, field_id)
        for res_id in self.env[field_id.relation].search(domain):
            record = {groupby[0]: (res_id.id, res_id.name), '__record_ids': [], f'{groupby[0]}_count': 0}
            final_result['groups'].append(record)

    def _planning_add_empty_records_domain(self, res_ids, field_id):
        if field_id.relation == 'resource.resource':
            return [('resource_type', '=', 'user'), ('id', 'not in', res_ids)]
        return [('id', 'not in', res_ids)]

    @api.model
    def planning_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        """Get unavailabilities data to display in the Gantt view.

        This method is meant to be overriden by each model that want to
        implement this feature on a Gantt view. A subslot is considered
        unavailable (and greyed) when totally covered by an unavailability.

        Example:
            * start_date = 01/01/2000, end_date = 01/07/2000, scale = 'week',
              rows = [{
                groupedBy: ["project_id", "user_id", "stage_id"],
                resId: 8,
                rows: [{
                    groupedBy: ["user_id", "stage_id"],
                    resId: 18,
                    rows: [{
                        groupedBy: ["stage_id"],
                        resId: 3,
                        rows: []
                    }, {
                        groupedBy: ["stage_id"],
                        resId: 9,
                        rows: []
                    }]
                }, {
                    groupedBy: ["user_id", "stage_id"],
                    resId: 22,
                    rows: [{
                        groupedBy: ["stage_id"],
                        resId: 9,
                        rows: []
                    }]
                }]
            }, {
                groupedBy: ["project_id", "user_id", "stage_id"],
                resId: 9,
                rows: [{
                    groupedBy: ["user_id", "stage_id"],
                    resId: None,
                    rows: [{
                        groupedBy: ["stage_id"],
                        resId: 3,
                        rows: []
                    }]
            }, {
                groupedBy: ["project_id", "user_id", "stage_id"],
                resId: 27,
                rows: []
            }]

            * The expected return value of this function is the rows dict with
              a new 'unavailabilities' key in each row for which you want to
              display unavailabilities. Unavailablitities is a list
              (naturally ordered and pairwise disjoint) in the form:
              [{
                  start: <start date of first unavailabity in UTC format>,
                  stop: <stop date of first unavailabity in UTC format>
              }, {
                  start: <start date of second unavailabity in UTC format>,
                  stop: <stop date of second unavailabity in UTC format>
              }, ...]

              To display that Marcel is unavailable January 2 afternoon and
              January 4 the whole day in his To Do row, this particular row in
              the rows dict should look like this when returning the dict at the
              end of this function :
              { ...
                {
                    groupedBy: ["stage_id"],
                    resId: 3,
                    rows: []
                    unavailabilities: [{
                        'start': '2018-01-02 14:00:00',
                        'stop': '2018-01-02 18:00:00'
                    }, {
                        'start': '2018-01-04 08:00:00',
                        'stop': '2018-01-04 18:00:00'
                    }]
                }
                ...
              }



        :param datetime start_date: start date
        :param datetime stop_date: stop date
        :param string scale: among "day", "week", "month" and "year"
        :param None | list[str] group_bys: group_by fields
        :param dict rows: dict describing the current rows of the gantt view
        :returns: dict of unavailability
        """
        return rows

    @api.model
    def planning_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        """Get progress bar value per record.

        This method is meant to be overriden by each related model that want to
        implement this feature on Gantt groups. The progressbar is composed
        of a value and a max_value given for each groupedby field.

        Example:
            fields = ['foo', 'bar'],
            res_ids = {'foo': [1, 2], 'bar':[2, 3]}
            start_date = 01/01/2000, end_date = 01/07/2000,
            self = base()

        Result:
            {
                'foo': {
                    1: {'value': 50, 'max_value': 100},
                    2: {'value': 25, 'max_value': 200},
                },
                'bar': {
                    2: {'value': 65, 'max_value': 85},
                    3: {'value': 30, 'max_value': 95},
                }
            }

        :param list fields: fields on which there are progressbars
        :param dict res_ids: res_ids of related records for which we need to compute progress bar
        :param string date_start_str: start date
        :param string date_stop_str: stop date
        :returns: dict of value and max_value per record
        """
        return {}
