/** @odoo-module **/

import {
    Component,
    useRef,
    useState,
    reactive,
    onWillUpdateProps,
    onWillRender,
    onMounted,
    useExternalListener,
    toRaw
} from "@odoo/owl";

// Core
import { _lt, _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { sortBy } from "@web/core/utils/arrays";
import { omit } from "@web/core/utils/objects";
import { url } from "@web/core/utils/urls";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { Domain } from "@web/core/domain";

// Views
import { formatFloatTime } from "@web/views/fields/formatters";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

// Helpers
import { removeDomainLeaves } from "./domain/domain";
import { evaluateBooleanExpr } from "./py_js/py";
import {
    dateAddFixedOffset,
    getCellColor,
    getColorIndex,
    usePlanningDraggable,
    usePlanningUndraggable,
    usePlanningResizable,
    usePlanningConnectorDraggable,
} from "./planning_helpers";
import { formatDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";

// Hooks
import { useService } from '@web/core/utils/hooks';
import { useViewCompiler, useVirtual } from "./hooks";
import { usePopover } from "./popover/popover_hooks";

// Components
import { PlanningCompiler } from "./planning_compiler";
import { PlanningCellButtons } from "./planning_cell_buttons";
import { PlanningPopover } from "./popover/planning_popover";
import { computeRange } from "./planning_model";
import { PlanningRowProgressBar } from "./planning_row_progress_bar";

const { Duration, DateTime } = luxon;

const INTERACTION_CLASSNAMES = [
    ["copy", "o_copying"],
    ["locked", "o_grabbing_locked"],
    ["reschedule", "o_grabbing"],
    ["resize", "o_resizing"],
];
const NEW_CONNECTOR_ID = "__connector__new";

export class PlanningRenderer extends Component {

    static components = { PlanningCellButtons, Popover: PlanningPopover, PlanningRowProgressBar };

    static template = "of_web_planning_view.PlanningRenderer";
    static headerTemplate = "of_web_planning_view.PlanningRenderer.Header";
    static rowContentTemplate = "of_web_planning_view.PlanningRenderer.RowContent";
    static rowHeaderTemplate = "of_web_planning_view.PlanningRenderer.RowHeader";
    static pillTemplate = "of_web_planning_view.PlanningRenderer.Pill";
    static totalRowTemplate = "of_web_planning_view.PlanningRenderer.TotalRow";

    static props = [
        "model",
        "arch",
        "class",
        "create",
        "openDialog",
        "scrollPosition?",
        "contentRef?",
    ];

    static GRID_ROW_HEIGHT = 4; // Pixels
    static GROUP_ROW_SPAN = 6; // --> 24 pixels
    static ROW_SPAN = 9; // --> 36 pixels
    static GRID_ROW_HEIGHT_WEEK = 8; // --> 32 Pixels
    static ROW_SPAN_WEEK = 9; // --> 72 pixels

    static getRowHeaderWidth(width) {
        return width > 768 ? 380 : 130;
    }

    setup() {
        this.model = this.props.model;

        this.cellContainerRef = useRef("cellContainer");
        this.rootRef = useRef("root");

        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.userService = useService("user");

        /** @type {HoveredInfo} */
        this.hovered = {
            connector: null,
            hoverable: null,
            pill: null,
        };

        this.state = useState({ rowHeaderWidth: 0 });

        /** @type {Interaction} */
        this.interaction = reactive(
            {
                mode: null,
                dragAction: "reschedule",
            },
            () => this.onInteractionChange()
        );
        this.onInteractionChange(); // Used to hook into "interaction"

        /** @type {CellButtonsProps} */
        this.cellButtonsProps = {
            reactive: reactive({ cell: null, dayCell: null }),
            canCreate: this.model.metaData.canCellCreate,
            canPlan: this.model.metaData.canPlan,
            onCreate: this.onCreate.bind(this),
            onPlan: this.onPlan.bind(this),
            scale: this.model.metaData.scale,
        };

        /** @type {Column[]} */
        this.columns = [];
        /** @type {DateTime[]} */
        this.dateGridColumns = [];
        /** @type {Pill[]} */
        this.extraPills = [];
        /** @type {Row[]} */
        this.extraRows = [];
        /** @type {Record<PillId, Pill>} */
        this.pills = {}; // mapping to retrieve pills from pill ids
        /** @type {RowId[]} */
        this.rowIds = [];
        /** @type {Row[]} */
        this.rows = [];
        /** @type {SubColumn[]} */
        this.subColumns = [];

        /** @type {Record<ConnectorId, ConnectorProps>} */
        this.connectors = reactive({});
        this.progressBarsReactive = reactive({ el: null });

        const position = localization.direction === "rtl" ? "bottom" : "right";
        this.popover = usePopover(this.constructor.components.Popover, { position });

        const { popoverTemplate } = this.model.metaData;
        if (popoverTemplate) {
            this.popoverTemplate = useViewCompiler(PlanningCompiler, {
                popoverTemplate,
            }).popoverTemplate;
        }

        this.throttledOnPointerMove = throttleForAnimation((ev) => this.onPointerMove(ev));

        useExternalListener(window, "keydown", (ev) => this.onWindowKeyDown(ev));
        useExternalListener(window, "keyup", (ev) => this.onWindowKeyUp(ev));

        const computeColumnWidth = debounce(() => this.computeColumnWidth(), 100);

        this.cellForDrag = { el: null, part: 0 };

        useExternalListener(window, "resize", computeColumnWidth);

        /** @type {Row[]} */
        this.virtualRows = useVirtual({
            getItems: () => this.rows,
            getItemHeight: (row) => this.getRowHeight(row),
            initialScroll: this.props.scrollPosition,
            scrollableRef: this.props.contentRef,
        });

        // Draggable pills
        this.cellForDrag = { el: null, part: 0 };
        const dragState = usePlanningDraggable({
            ref: this.rootRef,
            hoveredCell: this.cellForDrag,
            elements: ".o_draggable",
            ignore: ".o_resize_handle,.o_connector_creator_bullet",
            cells: ".o_planning_cell",
            // Style classes
            cellDragClassName: "o_planning_cell o_drag_hover",
            ghostClassName: "o_dragged_pill_ghost",
            // Handlers
            onDragStart: ({ pill }) => {
                this.popover.close();
                this.setStickyRowFromCell(this.cellForDrag.el);
                pill.classList.add("o_dragged")
                this.interaction.mode = "drag";
            },
            onDragEnd: ({ pill }) => {
                this.setStickyRowFromCell(null);
                pill.classList.remove("o_dragged")
                this.interaction.mode = null;
            },
            onDrop: (params) => {
                this.dragPillDrop(params);
            },
        });

        // Un-draggable pills
        const unDragState = usePlanningUndraggable({
            // Refs and selectors
            ref: this.rootRef,
            elements: ".o_undraggable",
            ignore: ".o_resize_handle,.o_connector_creator_bullet",
            edgeScrolling: { enabled: false },
            // Handlers
            onDragStart: ({ pill }) => {
                this.interaction.mode = "locked";
            },
            onDragEnd: ({ pill }) => {
                this.interaction.mode = null;
            },
        });

        // Resizable pills
        const resizeState = usePlanningResizable({
            // Refs and selectors
            ref: this.cellContainerRef,
            elements: ".o_resizable",
            innerPills: ".o_planning_pill",
            cells: ".o_planning_cell",
            // Other params
            handles: "o_resize_handle",
            rtl: () => localization.direction === "rtl",
            precision: () => this.model.metaData.scale.cellPart,
            // Handlers
            onDragStart: ({ pill }) => {
                this.popover.close();
                pill.classList.add("o_resized")
                this.interaction.mode = "resize";
            },
            onDrag: ({ pill, direction, diff }) => {
                const rect = pill.getBoundingClientRect();
                const position = { top: rect.y + rect.height };
                if (direction === "start") {
                    position.left = rect.x;
                } else {
                    position.right = document.body.offsetWidth - rect.x - rect.width;
                }
                const { cellTime, unitDescription } = this.model.metaData.scale;
            },
            onDragEnd: ({ pill }) => {
                pill.classList.remove("o_resized")
                this.interaction.mode = null;
            },
            onDrop: (params) => this.resizePillDrop(params),
        });

        // Draggable connector
        let initialPillId;
        this.connectorDragState = usePlanningConnectorDraggable({
            ref: this.rootRef,
            elements: ".o_connector_creator_bullet",
            parentWrapper: ".o_planning_cells .o_planning_pill_wrapper",
            onDragStart: ({ sourcePill, x, y }) => {
                this.popover.close();
                initialPillId = sourcePill.dataset.pillId;
                sourcePill.classList.add("o_connector_creator_show");
                this.setConnector({
                    id: NEW_CONNECTOR_ID,
                    highlighted: true,
                    sourcePoint: { left: x, top: y },
                    targetPoint: { left: x, top: y },
                });
            },
            onDrag: ({ x, y }) => {
                this.setConnector({ id: NEW_CONNECTOR_ID, targetPoint: { left: x, top: y } });
            },
            onDragEnd: () => {
                this.setConnector({ id: NEW_CONNECTOR_ID, sourcePoint: null, targetPoint: null });
            },
            onDrop: ({ target }) => {
                if (initialPillId === target.dataset.pillId) {
                    return;
                }
                const { id: masterId } = this.pills[initialPillId].record;
                const { id: slaveId } = this.pills[target.dataset.pillId].record;
                this.model.createDependency(masterId, slaveId);
            },
        });

        this.dragStates = [dragState, unDragState, resizeState];

        onWillUpdateProps(this.computeDerivedParams);
        onWillRender(this.onWillRender);
        onMounted(this.onMounted);

        this.computeDerivedParams();

    }

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get isDragging() {
        return this.dragStates.some((s) => s.dragging);
    }

    /**
     * @returns {boolean}
     */
    get isTouchDevice() {
        return isMobileOS() || hasTouch();
    }

    /**
     * @returns {number}
     */
    get pillHeight() {
        return this.constructor.GRID_ROW_HEIGHT * this.constructor.ROW_SPAN;
    }

    /**
     * @returns {number}
     */
    get rowHeight() {
        return this.constructor.GRID_ROW_HEIGHT;
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * @param {Pill} pill
     * @param {Group} group
     */
    addTo(pill, group) {
        group.pills.push(pill);
        group.aggregateValue += pill.record.duration;
        return true;
    }

    /**
     * Aggregates overlapping pills in group rows.
     *
     * @param {Pill[]} pills
     */
    aggregatePills(pills) {
        /** @type {Record<number, Group>} */
        const groups = {};
        for (let col = 1; col <= this.subColumns.length; col++) {
            groups[col] = {
                break: false,
                col,
                pills: [],
                aggregateValue: 0,
                grid: { column: [col, 1] },
            };
            // group.break = true means that the group cannot be merged with the previous one
            // We will merge groups that can be merged together (if this.shouldMergeGroups returns true)
        }

        for (const pill of pills) {
            let addedInPreviousCol = false;
            let col;
            for (col = this.getFirstcol(pill); col <= this.getLastCol(pill); col++) {
                const group = groups[col];
                const added = this.addTo(pill, group);
                if (addedInPreviousCol !== added) {
                    group.break = true;
                }
                addedInPreviousCol = added;
            }
            // here col = this.getLastCol(pill) + 1
            if (addedInPreviousCol && col <= this.subColumns.length) {
                groups[col].break = true;
            }
        }

        const filteredGroups = Object.values(groups).filter((g) => g.pills.length);

        if (this.shouldMergeGroups()) {
            return this.mergeGroups(filteredGroups);
        }

        return filteredGroups;
    }

    /**
     * Compute minimal levels required to display all pills without overlapping.
     * Side effect: level key is modified in pills.
     *
     * @param {Pill[]} pills
     */
    calculatePillsLevel(pills) {
        const firstPill = pills[0];
        firstPill.level = 0;
        const levels = [
            {
                pills: [firstPill],
                maxCol: this.getLastCol(firstPill),
            },
        ];
        for (const currentPill of pills.slice(1)) {
            const lastCol = this.getLastCol(currentPill);
            for (let l = 0; l < levels.length; l++) {
                const level = levels[l];
                if (this.getFirstcol(currentPill) > level.maxCol) {
                    currentPill.level = l;
                    level.pills.push(currentPill);
                    level.maxCol = lastCol;
                    break;
                }
            }
            if (isNaN(currentPill.level)) {
                currentPill.level = levels.length;
                levels.push({
                    pills: [currentPill],
                    maxCol: lastCol,
                });
            }
        }
        return levels.length;
    }

    /**
     * Returns the column indexes which fits both given dates inside
     * @param {DateTime} start
     * @param {DateTime} end
     * @param {DateTime[]} dates
     * @returns {[number, number]}
     */
    computeColumnIndexes(start, end, dates) {
        let startIndex =  0, endIndex;
        for (let index = 0; index < dates.length; index++) {
            if (dates[index].ts <= start) {
                startIndex = index;
            }
            if (dates[index].ts >= end) {
                endIndex = index;
                break;
            }
        }
        return [startIndex, endIndex];
    }

    computeColumns() {
        this.columns = [];
        this.subColumns = [];
        this.dateGridColumns = [];

        const { scale, startDate, stopDate } = this.model.metaData;
        const { cellPart, cellTime, interval, time } = scale;
        const now = DateTime.local();
        let cellIndex = 1;
        let colOffset = 1;
        let date;
        for (date = startDate; date <= stopDate; date = date.plus({ [interval]: 1 })) {
            const start = date;
            const stop = date.endOf(interval);
            const index = cellIndex++;
            const columnId = `__column__${index}`;
            const column = {
                id: columnId,
                grid: { column: [colOffset, cellPart] },
                start,
                stop,
            };
            const isToday = date.hasSame(now, "day");

            if (isToday) {
                column.isToday = true;
            }
            this.columns.push(column);

            for (let i = 0; i < cellPart; i++) {
                const subCellStart = dateAddFixedOffset(start, { [time]: i * cellTime });
                const subCellStop = dateAddFixedOffset(start, {
                    [time]: (i + 1) * cellTime,
                    seconds: -1,
                });
                this.subColumns.push({ start: subCellStart, stop: subCellStop, isToday, columnId });
                this.dateGridColumns.push(subCellStart);
            }

            colOffset += cellPart;
        }

        this.dateGridColumns.push(date);
    }

    computeColumnWidth() {
        const { cellPart } = this.model.metaData.scale;
        const subColumnCount = this.columns.length * cellPart;
        const totalWidth = window.innerWidth;
        const rowHeaderWidth = this.constructor.getRowHeaderWidth(totalWidth);
        const cellContainerWidth = totalWidth - rowHeaderWidth;
        this.state.rowHeaderWidth = rowHeaderWidth;
    }

    computeDerivedParams() {
        const { rows: modelRows } = this.model.data;

        this.topOffset = 0;
        this.nextPillId = 1;

        this.pills = {}; // mapping to retrieve pills from pill ids
        this.rows = [];
        this.rowIds = [];

        this.computeColumns();
        this.computeColumnWidth();

        const prePills = this.getPills();

        let pillsToProcess = [...prePills];
        for (const row of modelRows) {
            const result = this.processRow(row, pillsToProcess);
            this.rows.push(...result.rows);
            pillsToProcess = result.pillsToProcess;
        }

        this.gridTemplate = this.computeGrid(this.rows, this.columns);

        const { displayTotalRow } = this.model.metaData;
        if (displayTotalRow) {
            this.totalRow = this.getTotalRow(prePills);
        }
    }

    /**
     * @param {PointerEvent} ev
     */
    computeDerivedParamsFromHover(ev) {
        const { canCellCreate, canPlan, scale } = this.model.metaData;
        const { hoverable, pill } = this.hovered;
        // Update cell in drag
        const isCellHovered = hoverable?.matches(".o_planning_cell");

        this.cellForDrag.el = isCellHovered ? hoverable : null;
        this.cellForDrag.part = 0;
        if (isCellHovered && scale.cellPart > 1) {
            const rect = hoverable.getBoundingClientRect();
            const x = Math.floor(rect.x);
            const width = Math.floor(rect.width);
            this.cellForDrag.part = Math.floor((ev.clientX - x) / (width / scale.cellPart));
        }

        if (this.isDragging) {
            this.progressBarsReactive.el = null;
            this.cellButtonsProps.reactive.cell = null;
            this.cellButtonsProps.reactive.dayCell = null;
            return;
        }

        // Highlight pill
        const hoveredPillId = pill?.dataset.pillId;
        for (const pillId in this.pills) {
            if (pillId !== hoveredPillId) {
                this.togglePillHighlighting(pillId, false);
            }
        }
        this.togglePillHighlighting(hoveredPillId, true);

        // Update progress bars
        this.progressBarsReactive.el = hoverable;

        // Update cell buttons
        if (isCellHovered) {
            this.displayCellButtons(ev, hoverable, isCellHovered, canCellCreate, canPlan);
        }
    }

    displayCellButtons(ev, hoverable, isCellHovered, canCellCreate, canPlan) {
        if (ev && (canCellCreate || canPlan)) {
            if (isCellHovered) {
                // We also need cell dataset on click so we ensure this renderer updates the reactive prop
                this.cellButtonsProps.reactive.cell = hoverable;
            }
            const rowID = ev.target?.dataset.rowId;
            const colIndex = ev.target?.dataset.columnIndex;

            const buttonsCells = document.querySelectorAll('div.o_planning_cell_group_button');

            // Hide displayed buttons
            Array.from(buttonsCells).forEach(cell => {
                Array.from(cell.children).forEach(child => {
                    if (child.classList.contains('o_planning_cell_group_buttons_flex')) {
                        child.classList.remove('o_planning_cell_group_buttons_flex');
                        child.classList.add('o_planning_cell_group_buttons_hidden');
                    }
                });
            })

            // Display buttons for the hovered cell
            const buttonsCellsDiv = Array.from(buttonsCells).find(cell => {
                const cellRowID = cell.getAttribute('data-row-id');
                const cellColIndex = cell.getAttribute('data-column-index');
                return cellRowID === rowID && cellColIndex === colIndex;
            });

            if (buttonsCellsDiv) {
                for (let i = 0; i < buttonsCellsDiv.children.length; i++) {
                    buttonsCellsDiv.children[i].classList.remove('o_planning_cell_group_buttons_hidden');
                    buttonsCellsDiv.children[i].classList.add('o_planning_cell_group_buttons_flex');
                }
            }
        }
    }

    /**
     * @param {Row[]} rows
     * @param {Column[]} columns
     * @returns {{ rows: number, columns: number }}
     */
    computeGrid(rows, columns) {
        const { cellPart } = this.model.metaData.scale;
        return {
            rows: rows.reduce((acc, row) => acc + row.grid.row[1], 0),
            columns: columns.length * cellPart,
        };
    }

    /**
     * @param {Object} params
     * @param {Element} params.pill
     * @param {Element} params.cell
     * @param {number} params.diff
     */
    async dragPillDrop({ pill, cell, diff }) {
        const { rowId } = cell.dataset;
        const { dateStartField, dateStopField, scale } = this.model.metaData;
        const { cellTime, time } = scale;
        const { record } = this.pills[pill.dataset.pillId];

        const start =
            diff && dateAddFixedOffset(record[dateStartField], { [time]: cellTime * diff });
        const stop = diff && dateAddFixedOffset(record[dateStopField], { [time]: cellTime * diff });

        const schedule = this.model.getSchedule({ rowId, start, stop });

        if (this.interaction.dragAction === "copy") {
            await this.model.copy(record.id, schedule, this.openPlanDialogCallback);
        } else {
            await this.model.reschedule(record.id, schedule, this.openPlanDialogCallback);
        }

        // If the pill lands on a closed group -> open it
        if (cell.classList.contains("o_planning_group") && this.model.isClosed(rowId)) {
            this.model.toggleRow(rowId);
        }
    }

    /**
     * @param {Group} group
     * @param {Group} previousGroup
     */
    getAggregateValue(group, previousGroup) {
        // both groups have the same pills by construction
        // here the aggregateValue is the pill count
        return group.aggregateValue;
    }

    /**
     * @param {Pill} pill
     */
    getLastCol(pill) {
        const [col, colspan] = pill.grid.column;
        return col + colspan - 1;
    }

    /**
     * @param {Pill} pill
     * @returns {number}
     */
    getFirstcol(pill) {
        return pill.grid.column[0];
    }

    /**
     * @returns {string}
     */
    getFormattedFocusDate() {
        const { focusDate, scale } = this.model.metaData;
        const { format, id: scaleId, interval } = scale;
        switch (scaleId) {
            case "day": {
                const { startDate, stopDate } = this.model.metaData;
                const monday = formatDateTime(startDate, { format });
                const tuesday = formatDateTime(startDate.plus({ day: 1 }), { format });
                const wednesday = formatDateTime(startDate.plus({ day: 2 }), { format });
                const thursday = formatDateTime(startDate.plus({ day: 3 }), { format });
                const friday = formatDateTime(startDate.plus({ day: 4 }), { format });
                const saturday = formatDateTime(startDate.plus({ day: 5 }), { format });
                const sunday = formatDateTime(stopDate, { format });
                return [monday, tuesday, wednesday, thursday, friday, saturday, sunday];
            }
            case "week": {
                const { startDate, stopDate } = this.model.metaData;
                const start = formatDateTime(startDate, { format });
                const stop = formatDateTime(stopDate, { format });
                return `${start} - ${stop}`;
            }
            default:
                throw new Error(`Unknown scale id "${scaleId}".`);
        }
    }

    /**
     * @param {Pill} pill
     */
    getGroupPillDisplayName(pill) {
        return formatFloatTime(pill.aggregateValue);
    }

    /**
     * @param {Object} group
     * @param {number} maxAggregateValue
     * @param {boolean} consolidate
     */
    getPillFromGroup(group, maxAggregateValue, consolidate) {
        const { excludeField, field, maxValue } = this.model.metaData.consolidationParams;

        const minColor = 215;
        const maxColor = 100;

        const newPill = {
            id: `__pill__${this.nextPillId++}`,
            level: 0,
            aggregateValue: group.aggregateValue,
            grid: group.grid,
        };

        // Enrich the aggregates with consolidation data
        if (consolidate && field) {
            newPill.consolidationValue = 0;
            for (const pill of group.pills) {
                if (!pill.record[excludeField]) {
                    newPill.consolidationValue += pill.record[field];
                }
            }
            newPill.consolidationMaxValue = maxValue;
            newPill.consolidationExceeded =
                newPill.consolidationValue > newPill.consolidationMaxValue;
        }

        if (consolidate && maxValue) {
            const status = newPill.consolidationExceeded ? "danger" : "success";
            newPill.className = `bg-${status} border-${status}`;
            newPill.displayName = newPill.consolidationValue;
        } else {
            const color =
                minColor -
                Math.round((newPill.aggregateValue - 1) / maxAggregateValue) *
                    (minColor - maxColor);
            newPill.style = `background-color:rgba(${color},${color},${color},0.6)`;
            newPill.displayName = this.getGroupPillDisplayName(newPill);
        }

        return newPill;
    }

    /**
     * There are two forms of pills: pills comming from fetched records
     * and pills that are some kind of aggregation of the previous.
     *
     * Here we create the pills of the first type.
     *
     * The basic properties (independent of rows,...) of the pills of
     * the first type should be computed here.
     *
     * @returns {Partial<Pill>[]}
     */
    getPills() {
        const { records } = this.model.data;
        const { dateStartField } = this.model.metaData;
        const pills = [];
        for (const record of records) {
            const pill = this.getPill(record);
            pills.push(this.enrichPill(pill));
        }
        // sorting cannot be done when fetching data --> the snapping of pills breaks order
        return pills.sort(
            (p1, p2) =>
                p1.grid.column[0] - p2.grid.column[0] ||
                p1.record[dateStartField] - p2.record[dateStartField]
        );
    }

    /**
     * @param {PillId} pillId
     */
    getPillWrapperEl(pillId) {
        const pillSelector = `:scope > [data-pill-id="${pillId}"]`;
        return this.cellContainerRef.el?.querySelector(pillSelector);
    }

    /**
     * @param {RelationalRecord} record
     * @returns {Partial<Pill>}
     */
    getPill(record) {
        const { canEdit, dateStartField, dateStopField, disableDrag, startDate, stopDate } =
            this.model.metaData;

        const startOutside = record[dateStartField] < startDate;
        const stopOutside = record[dateStopField] > stopDate;

        /** @type {DateTime} */
        const pillStartDate = startOutside ? startDate : record[dateStartField];
        /** @type {DateTime} */
        const pillStopDate = stopOutside ? stopDate : record[dateStopField];

        const disableStartResize = !canEdit || startOutside;
        const disableStopResize = !canEdit || stopOutside;

        const [startIndex, stopIndex] = this.computeColumnIndexes(
            pillStartDate,
            pillStopDate,
            this.dateGridColumns
        );

        const firstCol = startIndex + 1;
        const span = stopIndex - startIndex;

        /** @type {Partial<Pill>} */
        return {
            disableDrag: disableDrag || disableStartResize || disableStopResize,
            disableStartResize,
            disableStopResize,
            grid: { column: [firstCol, span] },
            record,
            startDate: this.dateGridColumns[startIndex],
            stopDate: this.dateGridColumns[stopIndex],
        };
    }

    /**
     * @param {Partial<Pill>} pill
     * @returns {Pill}
     */
    enrichPill(pill) {
        const { colorField, fields, pillDecorations, tripBarFields } = this.model.metaData;
        const { displayTime, displayPrimary, displaySecondary, displayName } = this.getDisplayName(pill);
        pill.displayName = displayName;
        pill.displayTime = displayTime;
        pill.displayPrimary = displayPrimary;
        pill.displaySecondary = displaySecondary;

        const classes = [];

        if (pillDecorations) {
            const pillContext = Object.assign({}, this.userService.context);
            for (const [fieldName, value] of Object.entries(pill.record)) {
                const field = fields[fieldName];
                switch (field.type) {
                    case "date": {
                        pillContext[fieldName] = value ? serializeDate(value) : false;
                        break;
                    }
                    case "datetime": {
                        pillContext[fieldName] = value ? serializeDateTime(value) : false;
                        break;
                    }
                    default: {
                        pillContext[fieldName] = value;
                    }
                }
            }

            for (const decoration in pillDecorations) {
                const expr = pillDecorations[decoration];
                if (evaluateBooleanExpr(expr, pillContext)) {
                    classes.push(decoration);
                }
            }
        }

        if (colorField) {
            pill._color = getColorIndex(pill.record[colorField]);
            classes.push(`o_planning_color_${pill._color}`);
        }
        if (tripBarFields) {
            pill._trip = pill.record[tripBarFields] || 0;
            pill._tripDsp = `${pill._trip * 60 } min`;
        }

        pill.className = classes.join(" ");

        pill.allocatedHours = {};
        const recordIntervals = this.getRecordIntervals(pill.record);
        if (!recordIntervals.length) {
            return pill;
        }
        for (let col = this.getFirstcol(pill) - 1; col <= this.getLastCol(pill) + 1; col++) {
            const subColumn = this.subColumns[col - 1];
            if (!subColumn) {
                continue;
            }
            const { start, stop } = subColumn;
            const interval = [start, stop.plus({ seconds: 1 })];
            const union = getUnionOfIntersections(interval, recordIntervals);
            let duration = 0;
            for (const [otherStart, otherEnd] of union) {
                duration += otherEnd.diff(otherStart);
            }
            if (duration) {
                let minutes = Duration.fromMillis(duration * percentage).as("minute");
                minutes = Math.round(minutes / 5) * 5;
                pill.allocatedHours[col] = Duration.fromObject({ minutes }).as("hour");
            }
        }

        return pill;
    }

    /**
     * @param {RelationalRecord} record
     * @returns {any[]}
     */
    getRecordIntervals(record) {
        const val = record.of_resource_id;
        const resourceId = Array.isArray(val) ? val[0] : false;
        const { dateStartField, dateStopField } = this.model.metaData;
        const startTime = record[dateStartField];
        const endTime = record[dateStopField];
        if (!this.model.data.workIntervals) {
            return [];
        }
        const resourceIntervals = this.model.data.workIntervals[resourceId];
        if (!resourceIntervals) {
            return [];
        }
        const recordIntervals = getUnionOfIntersections([startTime, endTime], resourceIntervals);
        return recordIntervals;
    }

    /**
     * @param {number} columnIndex
     */
    getColumnStartStop(columnIndex) {
        const { start, stop } = this.columns[columnIndex];
        return { start, stop };
    }

    /**
     * This function will add a 'label' property to each
     * non-consolidated pill included in the pills list.
     * This new property is a string meant to replace
     * the text displayed on a pill.
     *
     * @param {Pill} pill
     */
    getDisplayName(pill) {
        const { computePillDisplayName, dateStartField, dateStopField, scale } =
            this.model.metaData;
        const { id: scaleId } = scale;
        const { record } = pill;

        if (!computePillDisplayName) {
            return record.display_name;
        }

        const startDate = record[dateStartField];
        const stopDate = record[dateStopField];
        const yearlessDateFormat = omit(DateTime.DATE_SHORT, "year");

        const spanAccrossDays = stopDate.startOf("day") > startDate.startOf("day");
        const spanAccrossWeeks =
            computeRange("week", stopDate).start > computeRange("week", startDate).start;

        /** @type {string[]} */
        const labelElements = [];

        /**
         * @type {{
         *   displayTime: string,
         *   displayPrimary: string,
         *   displaySecondary: string,
         *   displayName: string,
         * }}
         */
        const valuesToDisplay = {
            displayTime: "",
            displayPrimary: "",
            displaySecondary: "",
            displayName: "",
        };

        // Start & End Dates
        if (
            (scaleId === "day" && spanAccrossDays) ||
            (scaleId === "week" && spanAccrossWeeks)
        ) {
            labelElements.push(startDate.toLocaleString(yearlessDateFormat));
            labelElements.push(stopDate.toLocaleString(yearlessDateFormat));
        }

        // Start & End Times
        if (record.duration && ["week"].includes(scaleId)) {
            const durationStr = formatFloatTime(record.duration, {
                noLeadingZeroHour: true,
            }).replace(/(:00|:)/g, "h");
            labelElements.push(
                startDate.toFormat("t"),
                `${stopDate.toFormat("t")} (${durationStr})`
            );
        }

        // Time Text
        valuesToDisplay.displayTime = labelElements.join(" - ");

        // Primary Text
        valuesToDisplay.displayPrimary = record.display_name;
        // Secondary Text
        valuesToDisplay.displaySecondary = this.getSecondaryTextForPill(pill);

        // Original Display Name
        if (!record.of_allocated_hours || spanAccrossDays) {
            labelElements.push(record.display_name);
        }
        valuesToDisplay.displayName = labelElements.filter((el) => !!el).join(" - ");
        return valuesToDisplay;
    }

    /**
     *
     * @param {Pill} pill
     * @returns {string}
     */
    getSecondaryTextForPill(pill) {
        return "";
    }

    /**
     * @param {Group[]} groups
     * @returns {Group[]}
     */
    mergeGroups(groups) {
        if (groups.length <= 1) {
            return groups;
        }
        const index = Math.floor(groups.length / 2);
        const left = this.mergeGroups(groups.slice(0, index));
        const right = this.mergeGroups(groups.slice(index));
        const group = right[0];
        if (!group.break) {
            const previousGroup = left.pop();
            group.break = previousGroup.break;
            group.grid.column[0] = previousGroup.grid.column[0];
            group.grid.column[1] += previousGroup.grid.column[1];
            group.aggregateValue = this.getAggregateValue(group, previousGroup);
        }
        return [...left, ...right];
    }

    onWillRender() {
        this.visibleRows = [...new Set([...toRaw(this.virtualRows), ...this.extraRows])];
    }

    onMounted() { }

    /**
     * @param {Row} row
     * @param {Pill[]} pills
     */
    processRow(row, pills) {
        const { GROUP_ROW_SPAN, ROW_SPAN } = this.constructor;
        const { dependencyField, fields } = this.model.metaData;
        const {
            consolidate,
            fromServer,
            groupedByField,
            groupLevel,
            id,
            isGroup,
            name,
            progressBar,
            resId,
            rows,
            busy_time,
            unavailabilities,
            recordIds,
        } = row;

        // compute the subset pills at row level
        const remainingPills = [];
        let rowPills = [];
        const groupPills = [];
        const isMany2many = groupedByField && fields[groupedByField].type === "many2many";
        for (const pill of pills) {
            const { record } = pill;
            const pushPill = recordIds.includes(record.id);
            let keepPill = false;
            if (pushPill && isMany2many) {
                const value = record[groupedByField];
                if (Array.isArray(value) && value.length > 1) {
                    keepPill = true;
                }
            }
            if (pushPill) {
                const rowPill = { ...pill };
                rowPills.push(rowPill);
                groupPills.push(pill);
            }
            if (!pushPill || keepPill) {
                remainingPills.push(pill);
            }
        }

        const baseSpan = isGroup ? GROUP_ROW_SPAN : ROW_SPAN;
        let span = baseSpan;
        if (rowPills.length) {
            if (isGroup) {
                if (this.shouldComputeAggregateValues(row)) {
                    const groups = this.aggregatePills(rowPills);
                    const maxAggregateValue = Math.max(
                        ...groups.map((group) => group.aggregateValue)
                    );
                    rowPills = groups.map((group) =>
                        this.getPillFromGroup(group, maxAggregateValue, consolidate)
                    );
                } else {
                    rowPills = [];
                }
            } else {
                const level = this.calculatePillsLevel(rowPills);
                span = level * baseSpan + 4;
            }
        }
        if (progressBar && span === baseSpan && this.isTouchDevice) {
            // In mobile: rows span over 2 rows to alllow progressbars to properly display
            span += ROW_SPAN;
        }

        for (const rowPill of rowPills) {
            rowPill.id = `__pill__${this.nextPillId++}`;
            rowPill.grid = {
                ...rowPill.grid,
                row: [this.topOffset + rowPill.level * baseSpan + 1, baseSpan],
            };

            if (!isGroup) {
                const { record } = rowPill;
                if (this.shouldRenderRecordConnectors(record)) {
                    if (!this.mappingRecordToPillsByRow[record.id]) {
                        this.mappingRecordToPillsByRow[record.id] = {
                            masterIds: record[dependencyField],
                            pills: {},
                        };
                    }
                    this.mappingRecordToPillsByRow[record.id].pills[id] = rowPill;
                    if (!this.mappingRowToPillsByRecord[id]) {
                        this.mappingRowToPillsByRecord[id] = {};
                    }
                    this.mappingRowToPillsByRecord[id][record.id] = rowPill;
                }
            }

            this.pills[rowPill.id] = rowPill;
        }

        /** @type {Row} */
        const processedRow = {
            fromServer,
            groupedByField,
            groupLevel,
            id,
            isGroup,
            name,
            pills: rowPills,
            progressBar,
            resId,
            grid: {
                row: [this.topOffset + 1, span],
                column: [groupLevel + 2, -1],
            },
        };

        this.topOffset += span;

        const field = this.model.metaData.thumbnails[groupedByField];
        if (field) {
            let model = this.model.metaData.fields[groupedByField].relation;
            if (groupedByField === 'of_resource_id' && Boolean(resId)) {
                model = 'hr.employee';
            }
            processedRow.thumbnailUrl = url("/web/image", {
                model,
                id: resId,
                field,
            });
        }

        if (!isGroup && unavailabilities) {
            // attribute a color to each cell part according to row unavailabilities
            processedRow.cellColors = this.getRowCellColors(unavailabilities, busy_time);
        }
        else {
            processedRow.cellColors = {};
        }

        const result = { rows: [processedRow], pillsToProcess: remainingPills };

        let pillsToProcess = groupPills;
        if (isGroup && !this.model.isClosed(id)) {
            for (const subRow of rows) {
                const res = this.processRow(subRow, pillsToProcess);
                result.rows.push(...res.rows);
                pillsToProcess = res.pillsToProcess;
            }
        }

        return result;
    }

    /**
     * @param {Object} params
     * @param {Element} params.pill
     * @param {number} params.diff
     * @param {"start" | "end"} params.direction
     */
    async resizePillDrop({ pill, diff, direction }) {
        const { dateStartField, dateStopField, scale } = this.model.metaData;
        const { cellTime, time } = scale;
        const { record } = this.pills[pill.dataset.pillId];
        const params = {};

        if (direction === "start") {
            params.start = dateAddFixedOffset(record[dateStartField], { [time]: cellTime * diff });
        } else {
            params.stop = dateAddFixedOffset(record[dateStopField], { [time]: cellTime * diff });
        }
        const schedule = this.model.getSchedule(params);

        await this.model.reschedule(record.id, schedule, this.openPlanDialogCallback);
    }

    /**
     * @param {Row} row
     */
    getProgressBarProps(row) {
        return {
            progressBar: row.progressBar,
            reactive: this.progressBarsReactive,
            rowId: row.id,
        };
    }

    /**
     * Get domain of records for plan dialog in the gantt view.
     *
     * @param {Object} state
     * @returns {any[][]}
     */
    getPlanDialogDomain(params) {
        const { dateStartField, dateStopField } = this.model.metaData;
        const { start, stop } = params;

        // clean the domain from date fields
        const newDomain = removeDomainLeaves(
            this.env.searchModel.globalDomain,
            [dateStartField, dateStopField]
        );

        // search for records that are not assigned to a resource on the current day
        return Domain.and([
            newDomain,
            [
                [dateStartField, ">=", serializeDateTime(start)],
                [dateStopField, "<=", serializeDateTime(stop)],
                ["of_resource_id", "=", false],
            ],
        ]).toList({});
    }

    /**
     * @param {Pill} pill
     */
    getPopoverProps(pill) {
        const { record } = pill;
        let displayName = record.display_name;
        if (displayName.length > 60) {
            displayName = displayName.slice(0, 60) + '...';
        }
        const { canEdit, dateStartField, dateStopField } = this.model.metaData;
        const context = this.popoverTemplate
            ? { ...record }
            : /* Default context */ {
                name: displayName,
                start: record[dateStartField].toFormat("f"),
                stop: record[dateStopField].toFormat("f"),
            };

        return {
            title: displayName,
            context,
            template: this.popoverTemplate
        };
    }

    /**
     * @param {Row} row
     */
    getRowHeight(row) {
        return row.grid.row[1] * this.constructor.GRID_ROW_HEIGHT;
    }

    getRowTitleStyle(row) {
        return this.getGridPosition({ column: row.grid.column });
    }

    /**
     * @param {Unavailability[]} unavailabilities
     * @param {Busy Time[]} busy_time
     */
    getRowCellColors(unavailabilities, busy_time) {
        const { cellPart } = this.model.metaData.scale;
        // We assume that the unavailabilities have been normalized
        // (i.e. are naturally ordered and are pairwise disjoint).
        // A subCell is considered unavailable (and greyed) when totally covered by
        // an unavailability.
        let index = 0;
        let j = 0;
        /** @type {Record<string, string>} */
        const cellColors = {};
        const subSlotUnavailabilities = [];
        for (const subColumn of this.subColumns) {
            const { isToday, start, stop, columnId } = subColumn;

            // To account for the 5min precision
            const customStop = stop.minus({'minute': 55});

            if (unavailabilities.slice(index).length) {
                let subSlotUnavailable = 0;
                let occupied = false;
                if (busy_time  && busy_time.slice(index).length) {
                    for (let i = index; i < busy_time.length; i++) {
                        const u = busy_time[i];
                        if (customStop > u.stop) {
                            continue;
                        } else if (u.start <= start) {
                            subSlotUnavailable = 1;
                            occupied = true;
                            break;
                        }
                    }
                }
                if (subSlotUnavailable == 0) {
                    for (let i = index; i < unavailabilities.length; i++) {
                        const u = unavailabilities[i];
                        if (customStop > u.stop) {
                            continue;
                        } else if (u.start <= start) {
                            subSlotUnavailable = 1;
                            break;
                        }
                    }
                }
                subSlotUnavailabilities.push(subSlotUnavailable);

                if ((j + 1) % cellPart === 0) {
                    const style = getCellColor(cellPart, subSlotUnavailabilities, occupied, isToday);
                    subSlotUnavailabilities.splice(0, cellPart);
                    if (style) {
                        cellColors[columnId] = style;
                    }
                }
                j++;
            }
        }
        return cellColors;
    }

    /**
     * @param {{ column?: number | number[], row?: number | number[] }} position
     */
    getGridPosition(position) {
        const style = [];
        for (const prop of ["column", "row"]) {
            const [index, span] = Array.isArray(position[prop]) ? position[prop] : [position[prop]];
            if (span && span !== 1) {
                if (span === -1) {
                    style.push(`grid-${prop}:${index} / -1`);
                } else {
                    style.push(`grid-${prop}:${index} / span ${span}`);
                }
            } else if (index) {
                style.push(`grid-${prop}:${index}`);
            }
        }
        return style.join(";");
    }

    openPlanDialogCallback() {}

    async getSelectCreateDialogProps(params) {
        const domain = this.getPlanDialogDomain(params);
        const schedule = await this.model.getDialogContext(params);
        return {
            title: _t("Plan"),
            resModel: this.model.metaData.resModel,
            context: schedule,
            domain,
            onSelected: (resIds) => {
                if (resIds.length) {
                    this.model.assignTask(resIds, schedule, this.openPlanDialogCallback.bind(this));
                }
            },
        };
    }

    /**
     * @param {Pill[]} pills
     */
    getTotalRow(pills) {
        const preRow = {
            groupLevel: 0,
            id: "[]",
            isGroup: true,
            rows: [],
            name: _t("Total"),
            recordIds: pills.map(({ record }) => record.id),
        };

        this.topOffset = 0;
        const result = this.processRow(preRow, pills);
        const [totalRow] = result.rows;
        const maxAggregateValue = Math.max(...totalRow.pills.map((p) => p.aggregateValue));

        totalRow.factor = maxAggregateValue ? 90 / maxAggregateValue : 0;

        return totalRow;
    }

    highlightPill(pillId, highlighted) {
        const pill = this.pills[pillId];
        if (!pill) {
            return;
        }
        pill.highlighted = highlighted;
        this.getPillWrapperEl(pillId)?.classList.toggle("highlight", highlighted);
    }

    /**
     * @param {Row} row
     */
    isDisabled(row) {
        return this.model.useSampleModel;
    }

    /**
     * @param {Row} row
     */
    isHoverable(row) {
        return !this.model.useSampleModel;
    }

    /**
     * @param {HTMLElement | null} [cellEl]
     */
    setStickyRowFromCell(cellEl) {
        this.extraRows = [];
        if (cellEl) {
            const { rowId } = cellEl.dataset;
            const row = this.rows.find((row) => row.id === rowId);
            if (row) {
                this.extraRows.push(row);
            }
        }
    }

    /**
     * @param {Row} row
     */
    shouldComputeAggregateValues(row) {
        return true;
    }

    shouldMergeGroups() {
        return true;
    }

    /**
     * Returns whether connectors should be rendered or not.
     * The connectors won't be rendered on sampleData as we can't be sure that data are coherent.
     * The connectors won't be rendered on mobile as the usability is not guarantied.
     * The connectors won't be rendered on multiple groupBy as we would need to manage groups folding which seems
     *     overkill at this stage.
     *
     * @return {boolean}
     */
    shouldRenderConnectors() {
        return (
            this.model.metaData.dependencyField &&
            !this.model.useSampleModel &&
            !this.env.isSmall &&
            this.model.metaData.groupedBy.length <= 1
        );
    }

    /**
     * Returns whether connectors should be rendered on particular records or not.
     * This method is intended to be overridden in particular modules in order to set particular record's condition.
     *
     * @param {RelationalRecord} record
     * @return {boolean}
     */
    shouldRenderRecordConnectors(record) {
        return this.shouldRenderConnectors();
    }

    /**
     * @param {ConnectorId | null} connectorId
     * @param {boolean} highlighted
     */
    toggleConnectorHighlighting(connectorId, highlighted) {
        const connector = this.connectors[connectorId];
        if (!connector || (!connector.highlighted && !highlighted)) {
            return;
        }

        connector.highlighted = highlighted;
        connector.displayButtons = highlighted;

        const { sourcePillId, targetPillId } = this.mappingConnectorToPills[connectorId];

        this.highlightPill(sourcePillId, highlighted);
        this.highlightPill(targetPillId, highlighted);
    }

    /**
     * @param {PillId} pillId
     * @param {boolean} highlighted
     */
    togglePillHighlighting(pillId, highlighted) {
        const pill = this.pills[pillId];
        if (!pill || pill.highlighted === highlighted) {
            return;
        }

        const { record } = pill;
        const pillIdsToHighlight = new Set([pillId]);

        if (record && this.shouldRenderRecordConnectors(record)) {
            // Find other related pills
            const { pills: relatedPills } = this.mappingRecordToPillsByRow[record.id];
            for (const pill of Object.values(relatedPills)) {
                pillIdsToHighlight.add(pill.id);
            }

            // Highlight related connectors
            for (const [connectorId, connector] of Object.entries(this.connectors)) {
                const ids = Object.values(this.getRecordIds(connectorId));
                if (ids.includes(record.id)) {
                    connector.highlighted = highlighted;
                    connector.displayButtons = false;
                }
            }
        }

        // Highlight pills from found IDs
        for (const id of pillIdsToHighlight) {
            this.highlightPill(id, highlighted);
        }
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    onInteractionChange() {
        let { dragAction, mode } = this.interaction;
        if (mode === "drag") {
            mode = dragAction;
        }
        if (this.rootRef.el) {
            for (const [action, className] of INTERACTION_CLASSNAMES) {
                this.rootRef.el.classList.toggle(className, mode === action);
            }
        }
    }

    onPointerLeave() {
        this.throttledOnPointerMove.cancel();

        if (!this.isDragging) {
            const hoveredConnectorId = this.hovered.connector?.dataset.connectorId;
            this.toggleConnectorHighlighting(hoveredConnectorId, false);

            const hoveredPillId = this.hovered.pill?.dataset.pillId;
            this.togglePillHighlighting(hoveredPillId, false);
        }

        this.hovered.connector = null;
        this.hovered.pill = null;
        this.hovered.hoverable = null;

        this.computeDerivedParamsFromHover();
    }

    /**
     * Updates all hovered elements, then calls "computeDerivedParamsFromHover".
     *
     * @see computeDerivedParamsFromHover
     * @param {PointerEvent} ev
     */
    onPointerMove(ev) {
        // Lazily compute elements from point as it is a costly operation
        let els = null;
        const pointedEls = () => els || (els = document.elementsFromPoint(ev.clientX, ev.clientY));

        // To find hovered elements, also from pointed elements
        const find = (selector) =>
            ev.target.closest?.(selector) ||
            pointedEls().find((el) => el.matches(selector)) ||
            null;

        this.hovered.connector = find(".o_planning_connector");
        this.hovered.hoverable = find(".o_planning_hoverable");
        this.hovered.pill = find(".o_planning_pill_wrapper");

        this.computeDerivedParamsFromHover(ev);
    }

    /**
     * @param {PointerEvent} ev
     * @param {Pill} pill
     */
    onPillOpen(ev, pill) {
        if (this.popover.isOpen) {
            return;
        }
        const popoverTarget = ev.target.closest(".o_planning_pill_wrapper");
        this.popover.open(popoverTarget, this.getPopoverProps(pill));
    }

    /**
     * @param {PointerEvent} ev
     * @param {Pill} pill
     */
    onPillClose(ev, pill) {
        if (this.popover.isOpen) {
            this.popover.close();
        }
    }

    /**
     * @param {PointerEvent} ev
     * @param {Pill} pill
     */
    onPillDblClick(ev, pill) {
        console.log("onPillDblClick");
        const { record } = pill;
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.event",
                views: [[false, "form"]],
                res_id: record.id || false,
            },
            {}
        );
    }

    /**
     * @param {Object} params
     * @param {RowId} params.rowId
     * @param {number} params.columnIndex
     */
    async onCreate({ rowId, columnIndex }) {
        // use `this`here because we gonna get called from `PlanningWeekRenderer` or `PlanningDayRenderer`
        const { start, stop } = this.getColumnStartStop(columnIndex);
        const context = await this.model.getDialogContext({
            rowId,
            start,
            stop,
            withDefault: true,
        });
        this.props.create(context);
    }

    /**
     * @param {Object} params
     * @param {RowId} params.rowId
     * @param {number} params.columnIndex
     */
    async onPlan({ rowId, columnIndex }) {
        // use `this`here because we gonna get called from `PlanningWeekRenderer`
        const { start, stop } = this.getColumnStartStop(columnIndex);
        this.dialogService.add(
            SelectCreateDialog,
            await this.getSelectCreateDialogProps({ rowId, start, stop })
        )
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyDown(ev) {
        if (ev.key === "Control") {
            this.prevDragAction =
                this.interaction.dragAction === "copy" ? "reschedule" : this.interaction.dragAction;
            this.interaction.dragAction = "copy";
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyUp(ev) {
        if (ev.key === "Control") {
            this.interaction.dragAction = this.prevDragAction || "reschedule";
        }
    }
}
