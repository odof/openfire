/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { groupBy, unique } from "@web/core/utils/arrays";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { sprintf } from "@web/core/utils/strings";
import { pick } from "@web/core/utils/objects";
import { Model } from "@web/views/model";
import { formatFloat } from "@web/views/fields/formatters";
import { session } from "@web/session";

const GROUPBY_COMBINATIONS = ["of_resource_id"];

const { DateTime } = luxon;

/**
 * Returns start and end dates of the given scale (included), in local timezone.
 *
 * @param {ScaleId} scale
 * @param {DateTime} date DateTime object, in local timezone
 */
export function computeRange(scale, date) {
    let start = date;
    let end = date;

    if (scale === "week") {
        // startOf("week") does not depend on locale and will always give the
        // "Monday" of the week... (ISO standard)
        const { weekStart } = localization;
        const weekday = start.weekday < weekStart ? weekStart - 7 : weekStart;
        start = start.set({ weekday }).startOf("day");
        end = start.plus({ weeks: 1, days: -1 }).endOf("day");
    } else if (scale === "day") {
        // startOf("week") does not depend on locale and will always give the
        // "Monday" of the week... (ISO standard)
        const { weekStart } = localization;
        const weekday = start.weekday < weekStart ? weekStart - 7 : weekStart;
        start = start.set({ weekday }).startOf("day");
        end = start.plus({ weeks: 1, days: -1 }).endOf("day");
    } else {
        start = start.startOf(scale);
        end = end.endOf(scale);
    }

    return { start, end };
}

/**
 * @param {Record<string, Field>} fields
 * @param {Record<string, any>} values
 */
function parseServerValues(fields, values) {
    /** @type {Record<string, any>} */
    const parsedValues = {};
    if (!values) {
        return parsedValues;
    }
    for (const fieldName in values) {
        const field = fields[fieldName];
        const value = values[fieldName];
        switch (field.type) {
            case "date": {
                parsedValues[fieldName] = value ? deserializeDate(value) : false;
                break;
            }
            case "datetime": {
                parsedValues[fieldName] = value ? deserializeDateTime(value) : false;
                break;
            }
            case "selection": {
                if (value === false) {
                    // process selection: convert false to 0, if 0 is a valid key
                    const hasKey0 = field.selection.some((option) => option[0] === 0);
                    parsedValues[fieldName] = hasKey0 ? 0 : value;
                } else {
                    parsedValues[fieldName] = value;
                }
                break;
            }
            case "many2one": {
                parsedValues[fieldName] = value
                    ? [value.id, value.display_name]
                    : false;
                break;
            }
            default: {
                parsedValues[fieldName] = value;
            }
        }
    }
    return parsedValues;
}

export class PlanningModel extends Model {
    setup(params) {
        /** @type {Data} */
        this.data = {};
        /** @type {MetaData} */
        this.metaData = params.metaData;

        this.searchParams = null;
        this.start_hour = null;
        this.end_hour = null;
        this.defaultSearch = true;
        this.domainCopy = this.env.searchModel._domain;
        this.groupByCopy = this.env.searchModel._groupBy;
        this.orderByCopy = this.env.searchModel._orderBy;

        /** @type {Set<RowId>} */
        this.closedRows = new Set();

        // concurrency management
        this.keepLast = new KeepLast();
        this.mutex = new Mutex();
        /** @type {MetaData | null} */
        this._nextMetaData = null;
    }

    /**
     * @param {SearchParams} searchParams
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
        this.defaultSearch = _.isEqual(this.domainCopy, this.env.searchModel._domain) &&_.isEqual(this.groupByCopy, this.env.searchModel._groupBy) && _.isEqual(this.orderByCopy, this.env.searchModel._orderBy)

        await this._fetchData(this._buildMetaData(params));
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get date() {
        return this.metaData.focusDate;
    }
    get focusDate() {
        return this.metaData.focusDate;
    }
    get canCreate() {
        return this.metaData.canCreate && this.data.hasCreateRight;
    }
    get scale() {
        return this.metaData.scale;
    }
    get scales() {
        return this.metaData.scales;
    }

    /**
     * @param {"previous"|"next"} [direction]
     */
    async setFocusDate(direction) {
        const metaData = this._buildMetaData();
        let { focusDate, scale } = metaData;
        if (direction === "next") {
            focusDate = focusDate.plus({ week: 1 });
        } else if (direction === "previous") {
            focusDate = focusDate.minus({ week: 1 });
        } else {
            focusDate = DateTime.local();
        }
        await this.fetchData({ focusDate });
    }

    async getStartHour() {
        return await this.orm.call("res.company", "get_start_hour", [
            [session.company_id],
        ]);
    }

    async getEndHour() {
        return await this.orm.call("res.company", "get_end_hour", [
            [session.company_id],
        ]);
    }

    /**
     * @param {ScaleId} scaleId
     */
    async setScale(scaleId) {
        await this.fetchData({ scaleId });
    }

    async setUnaffectedRecords() {
        this.hideUnassignedRecords = !this.hideUnassignedRecords;
        await this.fetchData();
    }

    async fetchData(params) {
        await this._fetchData(this._buildMetaData(params));
        this.useSampleModel = false;
        this.notify();
    }

    /**
     * @param {Object} params
     * @param {RowId} [params.rowId]
     * @param {DateTime} [params.start]
     * @param {DateTime} [params.stop]
     * @param {boolean} [params.withDefault]
     * @returns {Record<string, any>}
     */
    async getDialogContext(params) {
        /** @type {Record<string, any>} */
        const context = { ...this.getSchedule(params) };
        if (params.withDefault) {
            if (context.of_resource_id && !context.of_employee_ids) {
                // get employee_id from resource_id if not already set
                const employee_id = await this.orm.call("hr.employee", "search", [
                    [["resource_id", "=", context.of_resource_id]],
                ]);
                if (employee_id.length) {
                    context.of_employee_ids = [employee_id[0]];
                    context.of_employee_id = employee_id[0];
                }
            }
            if (!context.of_company_id) {
                context.of_company_id = session.company_id;
            }
            for (const k in context) {
                context[sprintf("default_%s", k)] = context[k];
            }
        }

        Object.assign(context, this.searchParams.context);

        return context;
    }

    /**
     * @param {Object} params
     * @param {RowId} [params.rowId]
     * @param {DateTime} [params.start]
     * @param {DateTime} [params.stop]
     * @returns {Record<string, any>}
     */
    getSchedule({ rowId, start, stop, duration } = {}) {
        const { dateStartField, dateStopField, durationField, fields, groupedBy } = this.metaData;

        /** @type {Record<string, any>} */
        const schedule = {};

        if (duration) {
            schedule[durationField] = duration;
        }
        if (start) {
            schedule[dateStartField] = serializeDateTime(start);
        }
        if (stop && dateStartField !== dateStopField) {
            schedule[dateStopField] = serializeDateTime(stop);
        }
        if (rowId) {
            const group = Object.assign({}, ...JSON.parse(rowId));
            for (const fieldName of groupedBy) {
                if (fieldName in group) {
                    const value = group[fieldName];
                    if (Array.isArray(value)) {
                        const { type } = fields[fieldName];
                        schedule[fieldName] =
                            type === "many2many" ? [value[0]] : value[0];
                    } else {
                        schedule[fieldName] = value;
                    }
                }
            }
        }

        return schedule;
    }

    /**
     * @override
     * @returns {boolean}
     */
    hasData() {
        return Boolean(this.data.records.length);
    }

    /**
     * @param {RowId} rowId
     * @returns {boolean}
     */
    isClosed(rowId) {
        return this.closedRows.has(rowId);
    }

    /**
     * Removes from 'data' the fields holding the same value as the records targetted
     * by 'ids'.
     *
     * @template {Record<string, any>} T
     * @param {T} data
     * @param {number[]} ids
     * @returns {Partial<T>}
     */
    removeRedundantData(data, ids) {
        const records = this.data.records.filter((rec) => ids.includes(rec.id));
        if (!records.length) {
            return data;
        }

        /**
         *
         * @param {Record<string, any>} record
         * @param {Field} field
         */
        const isSameValue = (record, { name, type }) => {
            const recordValue = record[name];
            let newValue = data[name];
            if (Array.isArray(newValue)) {
                [newValue] = newValue;
            }
            if (Array.isArray(recordValue)) {
                if (type === "many2many") {
                    return recordValue.includes(newValue);
                } else {
                    return recordValue[0] === newValue;
                }
            } else if (["date", "datetime"].includes(type)) {
                return serializeDateTime(recordValue) === newValue;
            } else {
                return recordValue === newValue;
            }
        };

        /** @type {Partial<T>} */
        const trimmed = { ...data };

        for (const fieldName in data) {
            const field = this.metaData.fields[fieldName];
            if (records.every((rec) => isSameValue(rec, field))) {
                // All the records already have the given value.
                delete trimmed[fieldName];
            }
        }

        return trimmed;
    }

    /**
     * Reschedule a task to the given schedule.
     *
     * @param {number | number[]} ids
     * @param {Record<string, any>} schedule
     * @param {(result: any) => any} [callback]
     */
    async reschedule(ids, schedule, callback) {
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const allData = this._scheduleToData(schedule);
        const data = this.removeRedundantData(allData, ids);
        const context = this._getRescheduleContext();
        return this.mutex.exec(async () => {
            try {
                const result = await this.orm.write(this.metaData.resModel, ids, data, {
                    context,
                });
                if (callback) {
                    callback(result);
                }
            } finally {
                this.fetchData();
            }
        });
    }

    /**
     * Assign a task to the resource.
     *
     * @param {number | number[]} ids
     * @param {Record<string, any>} schedule
     * @param {(result: any) => any} [callback]
     */
    async assignTask(ids, schedule, callback) {
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const allData = this._scheduleToData(schedule);
        let data = this.removeRedundantData(allData, ids);
        data = { of_resource_id: data.of_resource_id }; // Keep only "of_resource_id" in data
        const context = this._getRescheduleContext();
        return this.mutex.exec(async () => {
            try {
                const result = await this.orm.write(this.metaData.resModel, ids, data, {
                    context,
                });
                if (callback) {
                    callback(result);
                }
            } finally {
                this.fetchData();
            }
        });
    }

    /**
     * @template {Record<string, any>} T
     * @param {T} schedule
     * @returns {Partial<T>}
     */
    _scheduleToData(schedule) {
        const allowedFields = [
            this.metaData.dateStartField,
            this.metaData.dateStopField,
            this.metaData.durationField,
            ...this.metaData.groupedBy,
        ];
        return pick(schedule, ...allowedFields);
    }

    /**
     * @param {string} rowId
     */
    toggleRow(rowId) {
        if (this.isClosed(rowId)) {
            this.closedRows.delete(rowId);
        } else {
            this.closedRows.add(rowId);
        }
        this.notify();
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * Recursive function to add progressBar info to rows grouped by the field.
     *
     * @protected
     * @param {string} fieldName
     * @param {Row[]} rows
     * @param {Record<number, ProgressBar>} progressBarInfo
     */
    _addProgressBarInfo(fieldName, rows, progressBarInfo) {
        for (const row of rows) {
            if (row.groupedByField === fieldName) {
                row.progressBar = progressBarInfo[row.resId];
                if (row.progressBar) {
                    row.progressBar.value_formatted = formatFloat(
                        row.progressBar.value,
                        {
                            digits: [false, 0],
                        }
                    );
                    row.progressBar.max_value_formatted = formatFloat(
                        row.progressBar.max_value,
                        {
                            digits: [false, 0],
                        }
                    );
                    row.progressBar.ratio = row.progressBar.max_value
                        ? (row.progressBar.value / row.progressBar.max_value) * 100
                        : 0;
                    row.progressBar.warning = progressBarInfo.warning;
                }
            } else {
                this._addProgressBarInfo(fieldName, row.rows, progressBarInfo);
            }
        }
    }

    /**
     * Compute rows for unavailability rpc call.
     *
     * @protected
     * @param {Row[]} [rows = []] in the format of ganttData.rows
     * @returns {Pick<Row, "groupedBy" | "resId" | "rows">[]} simplified rows only containing useful attributes
     */
    _computeUnavailabilityRows(rows = []) {
        return rows.map((row) => ({
            groupedBy: row.groupedBy,
            resId: row.resId,
            rows: this._computeUnavailabilityRows(row.rows),
        }));
    }

    /**
     * Check if the given groupedBy includes fields for which an empty fake group will be created
     *
     * @protected
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowCreateEmptyGroups(groupedBy) {
        return groupedBy.includes("of_resource_id");
    }

    /**
     * Check if the given groupBy is in the list that has to generate empty lines
     *
     * @protected
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowedEmptyGroups(groupedBy) {
        return GROUPBY_COMBINATIONS.includes(groupedBy.join(","));
    }

    /**
     * @protected
     */
    async _fetchData(metaData) {
        const { groupedBy, pagerLimit, pagerOffset, resModel } = metaData;
        const context = {
            ...this.searchParams.context,
            group_by: groupedBy,
        };
        const domain = this._getDomain(metaData);
        if (
            domain.some(
                ([fieldName, operator, value]) =>
                    fieldName === "of_resource_id" &&
                    operator === "=" &&
                    value === false
            )
        ) {
            this.hideUnassignedRecords = false;
        }
        const fields = this._getFields(metaData);
        const specification = {};
        for (const fieldName of fields) {
            specification[fieldName] = {};
            if (metaData.fields[fieldName].type === "many2one") {
                specification[fieldName].fields = { display_name: {} };
            }
        }

        // Load records
        const { length, groups, records } = await this.keepLast.add(
            this.orm.call(resModel, "get_planning_data", [], {
                domain,
                groupby: groupedBy,
                read_specification: specification,
                context,
                limit: pagerLimit,
                offset: pagerOffset,
            })
        );

        const rawRecords = records;

        groups.forEach((g) => (g.fromServer = true));

        const data = { count: length };

        data.records = this._parseServerData(metaData, rawRecords);
        data.rows = this._generateRows(metaData, {
            groupedBy,
            groups,
            parentGroup: [],
        });

        await this.keepLast.add(this._fetchDataPostProcess(metaData, data));

        this.data = data;
        this.metaData = metaData;
        this._nextMetaData = null;
    }

    //--------------------------------------------------------------------------

    /**
     * Get domain of records to display in the gantt view.
     *
     * @protected
     * @param {MetaData} metaData
     * @returns {any[]}
     */
    _getDomain(metaData) {
        const { dateStartField, dateStopField, startDate, stopDate } = metaData;
        let domain = Domain.and([
            this.searchParams.domain,
            [
                "&",
                [dateStartField, "<=", serializeDateTime(stopDate)],
                [dateStopField, ">=", serializeDateTime(startDate)],
            ],
        ]);
        // AS we are hiding unassigned records by default, we need to check if user has explicitly asked to display them
        // If not, we add a domain to hide them
        if (
            this.hideUnassignedRecords &&
            !domain
                .toList()
                .some(
                    ([fieldName, operator, value]) =>
                        fieldName === "of_resource_id" &&
                        operator === "=" &&
                        value === false
                )
        ) {
            domain = Domain.and([domain, [["of_resource_id", "!=", false]]]);
        }
        return domain.toList();
    }

    /**
     * Get all the fields needed.
     *
     * @protected
     * @param {MetaData} metaData
     * @returns {string[]}
     */
    _getFields(metaData) {
        const fields = new Set([
            "display_name",
            metaData.dateStartField,
            metaData.dateStopField,
            ...metaData.groupedBy,
            ...metaData.decorationFields,
        ]);
        if (metaData.colorField) {
            fields.add(metaData.colorField);
        }
        if (metaData.dependencyField) {
            fields.add(metaData.dependencyField);
        }
        if (metaData.tripBarFields) {
            fields.add(metaData.tripBarFields);
        }
        return [...fields];
    }

    /**
     * Format field value to display purpose.
     *
     * @protected
     * @param {any} value
     * @param {Object} field
     * @returns {string} formatted field value
     */
    _getFieldFormattedValue(value, field) {
        if (field.type === "boolean") {
            return value ? "True" : "False";
        } else if (!value) {
            return _t("Undefined %s", field.string);
        } else if (field.type === "many2many") {
            return value[1];
        }
        const formatter = registry.category("formatters").get(field.type);
        return formatter(value, field);
    }

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {{ groupBy: string[] }} searchParams
     * @returns {string[]}
     */
    _getGroupedBy(metaData, searchParams) {
        let groupedBy = [...searchParams.groupBy];
        groupedBy = this._filterDateIngroupedBy(metaData, groupedBy);
        if (!groupedBy.length) {
            groupedBy = metaData.defaultGroupBy;
        }
        return groupedBy;
    }

    /**
     * Remove date in groupedBy field
     *
     * @protected
     * @param {MetaData} metaData
     * @param {string[]} groupedBy
     * @returns {string[]}
     */
    _filterDateIngroupedBy(metaData, groupedBy) {
        return groupedBy.filter((gb) => {
            const [fieldName] = gb.split(":");
            const { type } = metaData.fields[fieldName];
            return !["date", "datetime"].includes(type);
        });
    }

    //--------------------------------------------------------------------------

    /**
     * Return a copy of this.metaData or of the last copy, extended with optional
     * params. This is useful for async methods that need to modify this.metaData,
     * but it can't be done in place directly for the model to be concurrency
     * proof (so they work on a copy and commit it at the end).
     *
     * @protected
     * @param {Object} params
     * @param {DateTime} [params.focusDate]
     * @param {string[]} [params.groupedBy]
     * @param {ScaleId} [params.scaleId]
     * @returns {MetaData}
     */
    _buildMetaData(params = {}) {
        this._nextMetaData = { ...(this._nextMetaData || this.metaData) };

        if (params.groupedBy) {
            this._nextMetaData.groupedBy = params.groupedBy;
        }

        let recomputeRange = false;
        if (params.scaleId) {
            this._nextMetaData.scale = { ...this.metaData.scales[params.scaleId] };
            recomputeRange = true;
        }
        if (params.focusDate) {
            this._nextMetaData.focusDate = params.focusDate;
            recomputeRange = true;
        }

        if ("pagerLimit" in params) {
            this._nextMetaData.pagerLimit = params.pagerLimit;
        }
        if ("pagerOffset" in params) {
            this._nextMetaData.pagerOffset = params.pagerOffset;
        }

        if (recomputeRange) {
            const { dynamicRange, focusDate, scale } = this._nextMetaData;
            if (dynamicRange) {
                this._nextMetaData.startDate = focusDate.startOf(scale.interval);
                this._nextMetaData.stopDate = this._nextMetaData.startDate.plus({
                    [scale.id]: 1,
                    millisecond: -1,
                });
            } else {
                const { start, end } = computeRange(scale.id, focusDate);
                this._nextMetaData.startDate = start;
                this._nextMetaData.stopDate = end;
            }
        }

        return this._nextMetaData;
    }

    //--------------------------------------------------------------------------

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {{ context: Record<string, any> }} searchParams
     * @returns {{ focusDate: DateTime, scaleId: ScaleId }}
     */
    _getInitialRangeParams(metaData, searchParams) {
        const { context } = searchParams;
        /** @type {ScaleId} */
        const scaleId = context.default_scale || metaData.defaultScale;
        /** @type {DateTime} */
        let focusDate =
            "initialDate" in context
                ? deserializeDateTime(context.initialDate)
                : DateTime.local();
        if (metaData.offset) {
            focusDate = focusDate.plus({ [scaleId]: metaData.offset });
        }
        return { focusDate, scaleId };
    }

    //--------------------------------------------------------------------------

    /**
     * Recursive function to get resIds of groups where the progress bar will be added.
     *
     * @protected
     * @param {string} fieldName
     * @param {Row[]} rows
     * @returns {number[]}
     */
    _getProgressBarResIds(fieldName, rows) {
        const resIds = [];
        for (const row of rows) {
            if (row.groupedByField === fieldName) {
                if (row.resId !== false) {
                    resIds.push(row.resId);
                }
            } else {
                resIds.push(...this._getProgressBarResIds(fieldName, row.rows || []));
            }
        }
        return [...new Set(resIds)];
    }

    _getRescheduleContext() {
        return { ...this.searchParams.context };
    }

    //--------------------------------------------------------------------------

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {Record<string, any>[]} records the server records to parse
     * @returns {Record<string, any>[]}
     */
    _parseServerData(metaData, records) {
        const {
            startDate: modelStartDate,
            stopDate: modelStopDate,
            dateStartField,
            dateStopField,
            fields,
        } = metaData;
        /** @type {Record<string, any>[]} */
        const parsedRecords = [];
        for (const record of records) {
            const parsedRecord = parseServerValues(fields, record);
            const dateStart = parsedRecord[dateStartField];
            const dateStop = parsedRecord[dateStopField];
            if (this.orm.isSample) {
                // In sample mode, we want enough data to be displayed, so we
                // swap the dates as the records are randomly generated anyway.
                if (dateStart > dateStop) {
                    parsedRecord[dateStartField] = dateStop;
                    parsedRecord[dateStopField] = dateStart;
                }
                // Record could also be outside the displayed range since the
                // sample server doesn't take the domain into account
                parsedRecord[dateStopField] = Math.max(
                    parsedRecord[dateStopField],
                    modelStartDate
                );
                parsedRecord[dateStartField] = Math.min(
                    parsedRecord[dateStartField],
                    modelStopDate
                );
                parsedRecords.push(parsedRecord);
            } else if (dateStart <= dateStop) {
                parsedRecords.push(parsedRecord);
            }
        }
        return parsedRecords;
    }

    //--------------------------------------------------------------------------

    /**
     * Process groups to generate a recursive structure according
     * to groupedBy fields. Note that there might be empty groups (filled by
     * read_goup with group_expand) that also need to be processed.
     *
     * @protected
     * @param {MetaData} metaData
     * @param {Object} params
     * @param {Object[]} params.groups
     * @param {string[]} params.groupedBy
     * @param {Object[]} params.parentGroup
     * @returns {Row[]}
     */
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
                rows.push(row);
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
    }

    //--------------------------------------------------------------------------

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {Data} data
     */
    async _fetchDataPostProcess(metaData, data) {
        const proms = [];
        if (metaData.displayUnavailability && !this.orm.isSample) {
            proms.push(this._fetchUnavailability(metaData, data));
        }

        if (metaData.progressBarFields && !this.orm.isSample) {
            const progressBarFields = metaData.progressBarFields.filter((f) =>
                metaData.groupedBy.includes(f)
            );
            if (progressBarFields.length) {
                proms.push(
                    this._fetchProgressBarData(metaData, data, progressBarFields)
                );
            }
        }
        await Promise.all(proms);
    }

    //--------------------------------------------------------------------------

    /**
     * Get progress bars info in order to display progress bar in gantt title column
     *
     * @protected
     * @param {MetaData} metaData
     * @param {Data} data
     * @param {string[]} progressBarFields
     */
    async _fetchProgressBarData(metaData, data, progressBarFields) {
        const resIds = {};
        let hasResIds = false;
        for (const fieldName of progressBarFields) {
            resIds[fieldName] = this._getProgressBarResIds(fieldName, data.rows);
            hasResIds = hasResIds || resIds[fieldName].length;
        }
        if (!hasResIds) {
            return;
        }

        const { resModel, scale, startDate } = metaData;
        const progressBarInfo = await this.orm.call(resModel, "planning_progress_bar", [
            progressBarFields,
            resIds,
            serializeDateTime(startDate),
            serializeDateTime(startDate.plus({ week: 1 })),
        ]);

        for (const fieldName in progressBarInfo) {
            this._addProgressBarInfo(fieldName, data.rows, progressBarInfo[fieldName]);
        }
    }

    //--------------------------------------------------------------------------

    /**
     * Fetches gantt unavailability.
     *
     * @protected
     * @param {MetaData} metaData
     * @param {Data} data
     */
    async _fetchUnavailability(metaData, data) {
        const enrichedRows = await this.orm.call(
            metaData.resModel,
            "planning_unavailability",
            [
                serializeDateTime(metaData.startDate),
                serializeDateTime(metaData.stopDate),
                metaData.scale.id,
                this.searchParams.domain,
                metaData.groupedBy,
                this._computeUnavailabilityRows(data.rows),
            ],
            {
                context: this.searchParams.context,
            }
        );
        // Update planningData.rows with the new unavailabilities data
        this._updateUnavailabilityRows(data.rows, enrichedRows);
    }

    //--------------------------------------------------------------------------

    /**
     * Recursive function to get resIds of groups where the progress bar will be added.
     *
     * @protected
     * @param {string} fieldName
     * @param {Row[]} rows
     * @returns {number[]}
     */
    _getProgressBarResIds(fieldName, rows) {
        const resIds = [];
        for (const row of rows) {
            if (row.groupedByField === fieldName) {
                if (row.resId !== false) {
                    resIds.push(row.resId);
                }
            } else {
                resIds.push(...this._getProgressBarResIds(fieldName, row.rows || []));
            }
        }
        return [...new Set(resIds)];
    }

    //--------------------------------------------------------------------------

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {string} groupedByField
     * @param {any} value
     * @returns {string}
     */
    _getRowName(metaData, groupedByField, value) {
        // Rename 'Undefined Resource' to ''.
        if (["of_resource_id"].includes(groupedByField)) {
            const resId = Array.isArray(value) ? value[0] : value;
            if (!resId) {
                return _t("Unassigned Interventions");
            }
        }
        const field = metaData.fields[groupedByField];
        return this._getFieldFormattedValue(value, field);
    }

    //--------------------------------------------------------------------------

    /**
     * Update rows with unavailabilities from enriched rows.
     *
     * @protected
     * @param {Row[]} original rows in the format of ganttData.rows
     * @param {Row[]} enriched rows as returned by the gantt_unavailability rpc call
     */
    _updateUnavailabilityRows(original, enriched) {
        for (let i = 0; i < original.length; i++) {
            const o = original[i];
            const e = enriched[i];
            if (e.unavailabilities) {
                o.unavailabilities = e.unavailabilities.map((u) => {
                    // These are new data from the server, they haven't been parsed yet
                    u.start = deserializeDateTime(u.start);
                    u.stop = deserializeDateTime(u.stop);
                    return u;
                });
            }
            if (e.busy_time) {
                o.busy_time = e.busy_time.map((u) => {
                    // These are new data from the server, they haven't been parsed yet
                    u.start = deserializeDateTime(u.start);
                    u.stop = deserializeDateTime(u.stop);
                    return u;
                });
            }
            if (o.rows && e.rows) {
                this._updateUnavailabilityRows(o.rows, e.rows);
            }
        }
    }
}
