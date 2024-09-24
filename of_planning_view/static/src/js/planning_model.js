/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { groupBy, unique } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { PlanningModel } from "@of_web_planning_view/js/planning_model";

patch(PlanningModel.prototype, "@of_planning_view/js/planning_model", {
    setup(params) {
        this._super(params);
        this.employeeIds = null;
    },

    /**
     * On réécrit ici toute la fonction load car la ligne qu'on veut y rajouter est à l'avant dernière ligne.
     * Utiliser un super ici déclencherait 2 fois un _fetchData
     */
    async load(searchParams) {
        const { context, domain } = searchParams;

        this.searchParams = searchParams;

        const metaData = this._buildMetaData();
        const params = {
            groupedBy: this._getGroupedBy(metaData, searchParams),
            pagerOffset: 0,
        };

        this.hideUnassignedRecords = true; // Hide unassigned records by default
        let displayUnassignedRecords = false;
        for (const node of domain) {
            if (
                node.length === 3 &&
                node[0] === "of_resource_id" &&
                node[1] !== "!=" &&
                node[2] !== false &&
                ["of_resource_id"].includes(node[0])
            ) {
                displayUnassignedRecords = true;
            }
        }
        if (displayUnassignedRecords) {
            searchParams.domain = Domain.or([
                domain,
                "[('of_resource_id', '=', false)]",
            ]).toList();
        }

        if (!metaData.scale) {
            Object.assign(
                params,
                this._getInitialRangeParams(this._buildMetaData(params), searchParams)
            );
        }

        this.start_hour = await this.getStartHour();
        this.end_hour = await this.getEndHour();
        this.defaultSearch =
            _.isEqual(this.domainCopy, this.env.searchModel._domain) &&
            _.isEqual(this.groupByCopy, this.env.searchModel._groupBy) &&
            _.isEqual(this.orderByCopy, this.env.searchModel._orderBy);

        // OF: On remplit ici employeeIds
        this.employeeIds = await this.getEmployees();
        // End OF

        await this._fetchData(this._buildMetaData(params));
    },

    /**
     * Fetches a list of employees who are either operators or salespersons.
     * If the searchParams contain a domain on the field `of_employee_ids`, we are replacing it by a domain on the field `name`
     * to ensure we get the correct employees even if they have no events.
     *
     * That ensure that we will not display planning lines for employees that are not in the list of employees.
     *
     * @returns {Promise<Array>} A promise that resolves to an array of employee records.
     */
    async getEmployees() {
        console.log("getEmployees");
        let employeeDomain = Domain.or([
            "[('of_is_operator', '=', true)]",
            "[('of_is_salesperson', '=', true)]",
        ]);

        if (!this.defaultSearch) {
            for (const domain of this.searchParams.domain) {
                if (domain[0] == "of_employee_ids") {
                    let cloneDomain = structuredClone(domain);
                    cloneDomain[0] = "name";
                    employeeDomain = Domain.and([
                        employeeDomain,
                        new Domain([cloneDomain]),
                    ]);
                }
            }
        }

        return await this.orm.search("hr.employee", employeeDomain.toList(), {});
    },

    _getGroupedBy(metaData, searchParams) {
        let groupedBy = [...searchParams.groupBy];
        groupedBy = this._filterDateIngroupedBy(metaData, groupedBy);

        // Le champs of_gb_employee_id ne fonctionne pas avec la vue planning,
        // qui est de base déjà groupée par ressource
        for (const [i, value] of groupedBy.entries()) {
            if (value == "of_gb_employee_id") {
                groupedBy[i] = "of_resource_id";
            }
        }

        if (!groupedBy.length) {
            groupedBy = metaData.defaultGroupBy;
        }

        return groupedBy;
    },

    _generateRows(metaData, params) {
        const { groupedBy, groups, parentGroup } = params;
        const groupLevel = metaData.groupedBy.length - groupedBy.length;

        if (!this.hideUnassignedRecords) {
            if (parentGroup.length === 0) {
                // _generateRows is a recursive function.
                // Here, we are generating top level rows.
                if (this._allowCreateEmptyGroups(groupedBy)) {
                    // The group with false values for every groupby can be absent from
                    // groups (= groups returned by read_group basically).
                    // Here we add the fake group {} in groups in any case (this simulates the group
                    // with false values mentionned above).
                    // This will force the creation of some rows with resId = false
                    // (e.g. 'Unassigned records') from top level to bottom level.
                    groups.push({});
                }
                if (this._allowedEmptyGroups(groupedBy)) {
                    params.addOpenShifts = true;
                }
            }
            if (params.addOpenShifts && groupedBy.length === 1) {
                // Here we are generating some rows on last level under a common
                // "parent" (if any: first level can be last level).
                // We make sure that a row with resId = false for
                // the unique groupby in groupedBy and same "parent" will be
                // added by adding a suitable fake group to the groups (a subset
                // of the groups returned by read_group).
                const fakeGroup = Object.assign({}, ...parentGroup);
                groups.push(fakeGroup);
            }
        }

        if (!groupedBy.length || !groups.length) {
            const recordIds = [];
            for (const g of groups) {
                recordIds.push(...(g.__record_ids || []));
            }
            return [
                {
                    groupLevel,
                    id: JSON.stringify([...parentGroup, {}]),
                    isGroup: false,
                    name: "",
                    recordIds: unique(recordIds),
                },
            ];
        }

        /** @type {Row[]} */
        const rows = [];

        // Some groups might be empty (thanks to expand_groups), so we can't
        // simply group the data, we need to keep all returned groups
        const groupedByField = groupedBy[0];
        const currentLevelGroups = groupBy(groups, (g) => {
            if (g[groupedByField] === undefined) {
                // we want to group the groups with undefined values for groupedByField with the ones
                // with false value for the same field.
                // we also want to be sure that stringification keeps groupedByField:
                // JSON.stringify({ key: undefined }) === "{}"
                // see construction of id below.
                g[groupedByField] = false;
            }
            return g[groupedByField];
        });
        const { maxField } = metaData.consolidationParams;
        const consolidate = groupLevel === 0 && groupedByField === maxField;
        const isGroup = maxField ? true : groupedBy.length > 1;
        for (const key in currentLevelGroups) {
            const subGroups = currentLevelGroups[key];
            const value = subGroups[0][groupedByField];
            const part = {};
            part[groupedByField] = value;
            const fakeGroup = [...parentGroup, part];
            const id = JSON.stringify(fakeGroup);
            const resId = Array.isArray(value) ? value[0] : value; // not really a resId
            const fromServer = subGroups.some((g) => g.fromServer);
            const recordIds = [];
            for (const g of subGroups) {
                recordIds.push(...(g.__record_ids || []));
            }
            const row = {
                consolidate,
                fromServer,
                groupedBy,
                groupedByField,
                groupLevel,
                id,
                isGroup,
                name: this._getRowName(metaData, groupedByField, value),
                resId, // not really a resId
                recordIds: unique(recordIds),
            };
            // if isGroup Generate sub rows
            if (isGroup) {
                row.rows = this._generateRows(metaData, {
                    ...params,
                    groupedBy: groupedBy.slice(1),
                    groups: subGroups,
                    parentGroup: fakeGroup,
                });
            }
            if (resId === false) {
                rows.unshift(row);
            } else {
                // OF : Display a row only if it's one of the employees
                if (
                    (this.employeeIds && this.employeeIds.includes(row.resId)) ||
                    row.recordIds.length
                ) {
                    rows.push(row);
                }
                // End OF
            }
        }

        // keep empty row to the head and sort the other rows alphabetically
        if (rows.length > 1) {
            rows.sort((a, b) => {
                if (a.resId && !b.resId) {
                    return 1;
                } else if (!a.resId && b.resId) {
                    return -1;
                } else {
                    return a.name.localeCompare(b.name);
                }
            });
        }
        return rows;
    },
});
