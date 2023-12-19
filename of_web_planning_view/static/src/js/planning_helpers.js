/** @odoo-module **/

import { useEffect } from "@odoo/owl";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";
import { clamp } from "@web/core/utils/numbers";
import { pick } from "@web/core/utils/objects";

/** @typedef {luxon.DateTime} DateTime */

/**
 * @param {number} target
 * @param {number[]} values
 * @returns {number}
 */
function closest(target, values) {
    return values.reduce(
        (prev, val) => (Math.abs(val - target) < Math.abs(prev - target) ? val : prev),
        Infinity
    );
}

/**
 * Adds a time diff to a date keeping the same value even if the offset changed
 * during the manipulation. This is typically needed with timezones using DayLight
 * Saving offset changes.
 *
 * @example dateAddFixedOffset(luxon.DateTime.local(), { hour: 1 });
 * @param {DateTime} date
 * @param {Record<string, number>} plusParams
 */
export function dateAddFixedOffset(date, plusParams) {
    const initialOffset = date.offset;
    const shouldApplyOffset = Object.keys(plusParams).some((key) =>
        /^(day|hour|minute|(milli)?second)s?$/i.test(key)
    );
    const result = date.plus(plusParams);
    const diff = initialOffset - result.offset;
    if (shouldApplyOffset && diff) {
        const adjusted = result.plus({ minute: diff });
        return adjusted.offset === initialOffset ? result : adjusted;
    } else {
        return result;
    }
}

/**
 * @param {number} cellPart
 * @param {(0 | 1)[]} subSlotUnavailabilities
 * @param {boolean} isToday
 * @returns {string | null}
 */
export function getCellColor(cellPart, subSlotUnavailabilities, busy, isToday) {
    const sum = subSlotUnavailabilities.reduce((acc, d) => acc + d);
    if (!sum && !busy) {
        return null;
    }
    switch (cellPart) {
        case sum: {
            return `background-color:${getCellPartColor(sum, busy, isToday)}`;
        }
        case 2: {
            const [c0, c1] = subSlotUnavailabilities.map((d) => getCellPartColor(d, busy, isToday));
            return `background:linear-gradient(90deg,${c0}49%,${c1}50%)`;
        }
        case 4: {
            const [c0, c1, c2, c3] = subSlotUnavailabilities.map((d) =>
                getCellPartColor(d, busy, isToday)
            );
            return `background:linear-gradient(90deg,${c0}24%,${c1}25%,${c1}49%,${c2}50%,${c2}74%,${c3}75%)`;
        }
    }
}

/**
 * @param {0 | 1} unavailable
 * @param {boolean} busy
 * @param {boolean} isToday
 * @returns {string}
 */
export function getCellPartColor(unavailable, busy, isToday) {
    if (busy) {
        return "var(--Planning__Busy-background-color)";
    } else if (isToday) {
        return "var(--Planning__DayOffToday-background-color)";
    } else if (unavailable) {
        return "var(--Planning__DayOff-background-color)";
    }
}

/**
 * @param {number | [number, string]} value
 * @returns {number}
 */
export function getColorIndex(value) {
    if (typeof value === "number") {
        return Math.round(value) % NB_GANTT_RECORD_COLORS;
    } else if (Array.isArray(value)) {
        return value[0] % NB_GANTT_RECORD_COLORS;
    }
    return 0;
}

/**
 * Intervals are supposed to intersect (intersection duration >= 1 milliseconds)
 *
 * @param {[DateTime, DateTime]} interval
 * @param {[DateTime, DateTime]} otherInterval
 * @returns {[DateTime, DateTime]}
 */
export function getIntersection(interval, otherInterval) {
    const [start, end] = interval;
    const [otherStart, otherEnd] = otherInterval;
    return [start >= otherStart ? start : otherStart, end <= otherEnd ? end : otherEnd];
}

/**
 * Computes intersection of a closed interval with a union of closed intervals ordered and disjoint
 * = a union of intersections
 *
 * @param {[DateTime, DateTime]} interval
 * @param {[DateTime, DateTime]} intervals
 * @returns {[DateTime, DateTime][]}
 */
export function getUnionOfIntersections(interval, intervals) {
    const [start, end] = interval;
    const intersecting = intervals.filter((otherInterval) => {
        const [otheStart, otherEnd] = otherInterval;
        return otherEnd > start && end > otheStart;
    });
    const len = intersecting.length;
    if (len === 0) {
        return [];
    }
    const union = [];
    const first = getIntersection(interval, intersecting[0]);
    union.push(first);
    if (len >= 2) {
        const last = getIntersection(interval, intersecting[len - 1]);
        union.push(...intersecting.slice(1, len - 1), last);
    }
    return union;
}

/**
 * @param {Object} params
 * @param {Ref<HTMLElement>} params.ref
 * @param {string} params.selector
 * @param {string} params.related
 * @param {string} params.className
 */
export function useMultiHover({ ref, selector, related, className }) {
    /**
     * @param {HTMLElement} el
     */
    const findSiblings = (el) =>
        ref.el.querySelectorAll(
            related
                .map((attr) => `[${attr}='${el.getAttribute(attr).replace(/'/g, "\\'")}']`)
                .join("")
        );

    /**
     * @param {PointerEvent} ev
     */
    const onPointerEnter = (ev) => {
        for (const sibling of findSiblings(ev.target)) {
            sibling.classList.add(...classList);
            classedEls.add(sibling);
        }
    };

    /**
     * @param {PointerEvent} ev
     */
    const onPointerLeave = (ev) => {
        for (const sibling of findSiblings(ev.target)) {
            sibling.classList.remove(...classList);
            classedEls.delete(sibling);
        }
    };

    const classList = className.split(/\s+/g);
    const classedEls = new Set();

    useEffect(
        (...targets) => {
            if (targets.length) {
                for (const target of targets) {
                    target.addEventListener("pointerenter", onPointerEnter);
                    target.addEventListener("pointerleave", onPointerLeave);
                }
                return () => {
                    for (const el of classedEls) {
                        el.classList.remove(...classList);
                    }
                    classedEls.clear();
                    for (const target of targets) {
                        target.removeEventListener("pointerenter", onPointerEnter);
                        target.removeEventListener("pointerleave", onPointerLeave);
                    }
                };
            }
        },
        () => [...ref.el.querySelectorAll(selector)]
    );
}

const NB_GANTT_RECORD_COLORS = 12;

// Resizable hook handles

const HANDLE_CLASS_START = "o_handle_start";
const HANDLE_CLASS_END = "o_handle_end";
const handles = {
    start: document.createElement("div"),
    end: document.createElement("div"),
};

// Draggable hooks

export const usePlanningConnectorDraggable = makeDraggableHook({
    name: "usePlanningConnectorDraggable",
    acceptedParams: {
        parentWrapper: ["string"],
    },
    onComputeParams({ ctx, params }) {
        ctx.parentWrapper = params.parentWrapper;
        ctx.followCursor = false;
    },
    onDragStart: ({ ctx, helpers }) => {
        const { currentElement } = ctx;
        const parent = currentElement.closest(ctx.parentWrapper);
        if (!parent) {
            return;
        }
        for (const otherParent of ctx.ref.el.querySelectorAll(ctx.parentWrapper)) {
            if (otherParent !== parent) {
                helpers.addStyle(otherParent, { pointerEvents: "auto" });
            }
        }
        helpers.execHandler("onDragStart", { sourcePill: parent });
    },
    onDrag: ({ ctx }) => {
        pick(ctx.current, "element"),
        helpers.execHandler("onDrag", {});
    },
    onDragEnd: ({ ctx }) => {
        pick(ctx.current, "element"),
        helpers.execHandler("onDragEnd", {});
    },
    onDrop: ({ ctx, target }) => {
        const { current } = ctx;
        const parent = current.element.closest(ctx.parentWrapper);
        const targetParent = target.closest(ctx.parentWrapper);
        if (!targetParent || targetParent === parent) {
            return;
        }
        helpers.execHandler("onDrop", { target: targetParent });
    },
});

export const usePlanningDraggable = makeDraggableHook({
    name: "usePlanningDraggable",
    acceptedParams: {
        cells: ["string", "function"],
        cellDragClassName: ["string", "function"],
        ghostClassName: ["string", "function"],
        hoveredCell: ["object"],
    },
    defaultParams: {
        ghostElement: null,
    },
    onComputeParams({ ctx, params }) {
        ctx.cellSelector = params.cells;
        ctx.ghostClassName = params.ghostClassName;
        ctx.cellDragClassName = params.cellDragClassName;
        ctx.hoveredCell = params.hoveredCell;
        ctx.ghostElement = params.ghostElement;
    },
    onWillStartDrag({ ctx, helpers }) {
        const { currentElement } = ctx;
        const { el: cell, part } = ctx.hoveredCell;

        currentElement.placeHolder = currentElement.cloneNode(true);
        ctx.ghostElement = currentElement.placeHolder;
        currentElement.cellGhost = document.createElement("div");
        currentElement.cellGhost.className = ctx.cellDragClassName;
        currentElement.cell = { el: null, index: null, part: 0 };

        const gridStyle = getComputedStyle(cell.parentElement);
        const pillStyle = getComputedStyle(currentElement);
        const cellStyle = getComputedStyle(cell);

        const gridTemplateColumns = gridStyle.getPropertyValue("grid-template-columns");
        const pGridColumnStart = Number(pillStyle.getPropertyValue("grid-column-start"));
        const pGridColumnEnd = pillStyle.getPropertyValue("grid-column-end");
        const cGridColumnStart = Number(cellStyle.getPropertyValue("grid-column-start")) + part;
        const spanMatch = pGridColumnEnd.match(/span (\d+)/);
        const highestGridIndex = gridTemplateColumns.split(" ").length + 1;
        const pillSpan = spanMatch ? Number(spanMatch[1]) : 1;

        currentElement.initialIndex = pGridColumnStart - 1;
        currentElement.maxGridColumnStart = highestGridIndex - pillSpan;
        currentElement.gridColumnOffset = pGridColumnStart - cGridColumnStart;
        currentElement.gridColumnEnd = pillStyle.getPropertyValue("grid-column-end");

        helpers.addStyle(ctx.ref.el, { pointerEvents: "auto" });
        helpers.execHandler("onWillStartDrag", { element: currentElement });
    },
    onDragStart({ ctx, helpers }) {
        const { cellSelector, currentElement, ghostClassName } = ctx;
        for (const cell of ctx.ref.el.querySelectorAll(cellSelector)) {
            helpers.addStyle(cell, { pointerEvents: "auto" });
        }
        currentElement.before(currentElement.placeHolder);
        if (ghostClassName) {
            currentElement.placeHolder.classList.add(ghostClassName);
        }
        helpers.execHandler("onDragStart", { pill: currentElement });
    },
    onDrag({ ctx, helpers  }) {
        const { cellSelector, currentElement, hoveredCell } = ctx;
        let { el: cell, part } = hoveredCell;

        const isDifferentCell = cell !== currentElement.cell.el;
        const isDifferentPart = part !== currentElement.cell.part;

        if (cell && !cell.matches(cellSelector)) {
            cell = null; // Not a cell
        }

        currentElement.cell.el = cell;
        currentElement.cell.part = part;

        if (cell) {
            // Recompute cell style if in a different cell
            if (isDifferentCell) {
                const style = getComputedStyle(cell);
                currentElement.cell.gridRow = style.getPropertyValue("grid-row");
                currentElement.cell.gridColumnStart =
                    Number(style.getPropertyValue("grid-column-start")) + currentElement.gridColumnOffset;
            }
            // Assign new grid coordinates if in different cell or different cell part
            if (isDifferentCell || isDifferentPart) {
                const { gridColumnEnd } = currentElement;
                const { gridRow, gridColumnStart: start } = currentElement.cell;
                const gridColumnStart = clamp(start + part, 1, currentElement.maxGridColumnStart);

                helpers.addStyle(currentElement.cellGhost, { gridRow, gridColumnStart, gridColumnEnd });

                currentElement.cell.index = gridColumnStart - 1; // Grid incides start at 1
            }
        } else {
            currentElement.cell.index = null;
        }

        // Attach or remove cell ghost
        if (isDifferentCell) {
            if (cell) {
                cell.after(currentElement.cellGhost);
            } else {
                currentElement.cellGhost.remove();
            }
        }

        return { pill: currentElement };
    },
    onDragEnd({ ctx, helpers }) {
        helpers.execHandler("onDragEnd", { pill: ctx.currentElement });
    },
    onDrop({ ctx, helpers }) {
        const { cell, initialIndex } = ctx.currentElement;
        if (cell.index !== null) {
            helpers.execHandler("onDrop", {
                pill: ctx.currentElement,
                cell: cell.el,
                diff: cell.index - initialIndex,
            });
        }
    },
    onCleanup({ ctx }) {
        const { ghostElement } = ctx;
        if (ghostElement) {
            ghostElement.remove()
        }
    },
});

export const usePlanningUndraggable = makeDraggableHook({
    name: "usePlanningUndraggable",
    getRect(el, options = {}) {
        const rect = el.getBoundingClientRect();
        if (options.adjust) {
            const style = getComputedStyle(el);
            const [pl, pr, pt, pb] = [
                "padding-left",
                "padding-right",
                "padding-top",
                "padding-bottom",
            ].map((prop) => pixelValueToNumber(style.getPropertyValue(prop)));

            rect.x += pl;
            rect.y += pt;
            rect.width -= pl + pr;
            rect.height -= pt + pb;
        }
        return rect;
    },
    onWillStartDrag({ ctx, helpers }) {
        const { x, y, width, height } = this.getRect(ctx.currentElement);
        ctx.currentContainer = document.createElement("div");

        helpers.addStyle(ctx.ref.el, { pointerEvents: "auto" });
        helpers.addStyle(ctx.currentContainer, {
            position: "fixed",
            left: `${x}px`,
            top: `${y}px`,
            width: `${width}px`,
            height: `${height}px`,
        });

        ctx.currentElement.after(ctx.currentContainer);
    },
    onDragStart({ ctx, helpers }) {
        helpers.execHandler("onDragStart", { pill: ctx.currentElement });
    },
    onDragEnd({ ctx, helpers }) {
        helpers.execHandler("onDronDragEndagStart", { pill: ctx.currentElement });
    },
    onCleanup({ ctx }) {
        const { currentContainer } = ctx;
        if (currentContainer) {
            currentContainer.remove()
        }
    },
});

export const usePlanningResizable = makeDraggableHook({
    name: "usePlanningResizable",
    requiredParams: ["handles"],
    acceptedParams: {
        innerPills: ["string", "function"],
        handles: ["string", "function"],
        rtl: ["boolean", "function"],
        cells: ["string", "function"],
        precision: ["number", "function"],
        showHandles: ["function"],
    },
    getRect(el, options = {}) {
        const rect = el.getBoundingClientRect();
        if (options.adjust) {
            const style = getComputedStyle(el);
            const [pl, pr, pt, pb] = [
                "padding-left",
                "padding-right",
                "padding-top",
                "padding-bottom",
            ].map((prop) => pixelValueToNumber(style.getPropertyValue(prop)));

            rect.x += pl;
            rect.y += pt;
            rect.width -= pl + pr;
            rect.height -= pt + pb;
        }
        return rect;
    },

    onComputeParams({ ctx, params, helpers }) {
        const onElementPointerEnter = (ev) => {
            if (ctx.dragging) {
                return;
            }

            const pill = ev.target;
            const innerPill = pill.querySelector(params.innerPills);

            const pillRect = this.getRect(innerPill);

            for (const el of Object.values(handles)) {
                el.style.height = `${pillRect.height}px`;
            }

            const showHandles = params.showHandles ? params.showHandles(pill) : {};
            if ("start" in showHandles && !showHandles.start) {
                handles.start.remove();
            } else {
                innerPill.appendChild(handles.start);
            }
            if ("end" in showHandles && !showHandles.end) {
                handles.end.remove();
            } else {
                innerPill.appendChild(handles.end);
            }
        };

        const onElementPointerLeave = () => {
            const remove = () => Object.values(handles).forEach((h) => h.remove());
            if (!ctx.dragging && !ctx.currentElement) {
                remove();
            }
        };

        ctx.cellSelector = params.cells;
        ctx.precision = params.precision;

        for (const el of ctx.ref.el.querySelectorAll(params.elements)) {
            el.addEventListener("pointerenter", onElementPointerEnter);
            el.addEventListener("pointerleave", onElementPointerLeave);
        }

        handles.start.className = `${params.handles} ${HANDLE_CLASS_START}`;
        handles.start.style.cursor = `${params.rtl ? "e" : "w"}-resize`;

        handles.end.className = `${params.handles} ${HANDLE_CLASS_END}`;
        handles.end.style.cursor = `${params.rtl ? "w" : "e"}-resize`;

        // Override "full" and "element" selectors: we want the draggable feature
        // to apply to the handles
        ctx.pillSelector = ctx.elementSelector;
        ctx.fullSelector = ctx.elementSelector = `.${params.handles}`;

        // Force the handles to stay in place
        ctx.followCursor = false;
    },
    onWillStartDrag({ ctx, helpers }) {
        const { cellSelector, currentElement, currentElementRect, currentContainer, mouse, pillSelector, precision } = ctx;

        ctx.cursor = getComputedStyle(currentElement).cursor;
        currentElement.pill = currentElement.closest(pillSelector);

        const pRect = this.getRect(currentElement.pill);
        const handleRect = this.getRect(currentElement);
        const { x: px, width: pw } = pRect;

        currentElement.isStart = currentElement.classList.contains(HANDLE_CLASS_START);
        currentElement.steps = [];

        let step;
        for (const cell of currentContainer.querySelectorAll(cellSelector)) {
            const cRect = this.getRect(cell);
            const posX = Math.floor(
                currentElement.isStart ? cRect.x : cRect.x + cRect.width - handleRect.width
            );
            step ||= cRect.width / precision;
            for (let i = 0; i < precision; i++) {
                const stepOffset = step * i;
                const x = currentElement.isStart ? posX + stepOffset : posX - stepOffset;
                if (
                    !currentElement.steps.includes(x) &&
                    ((currentElement.isStart && x <= px + pw - step) || (!currentElement.isStart && px <= x))
                ) {
                    currentElement.steps.push(x);
                }
            }
        }

        currentElement.steps.sort((a, b) => (currentElement.isStart ? b - a : a - b));

        currentElement.initialPillRect = pRect;
        currentElement.initialStep = closest(mouse.x, currentElement.steps);

        helpers.addStyle(ctx.ref.el, { pointerEvents: "auto" });
        helpers.execHandler("onWillStartDrag", {});
    },
    onDragStart({ ctx, helpers }) {
        const parent = ctx.currentElement.closest(ctx.pillSelector);
        const pRect = this.getRect(ctx.currentElement.pill);

        helpers.addStyle(ctx.currentElement.pill, {
            position: "fixed",
            left: `${ctx.currentElement.initialPillRect.x}px`,
            top: `${pRect.y}px`,
            width: `${pRect.width}px`,
            height: `${pRect.height}px`,
            zIndex: 100,
        });
        helpers.execHandler("onDragStart", { pill: parent });
    },
    onDrag({ ctx, helpers }) {
        const { currentElement, currentElementRect, mouse, pillSelector } = ctx;
        const closestStep = closest(mouse.x, currentElement.steps);
        const { x, width } = currentElement.initialPillRect;

        if (closestStep === currentElement.lastStep) {
            return;
        }
        currentElement.lastStep = closestStep;

        helpers.addStyle(currentElement, { position: "absolute !important" });

        if (currentElement.isStart) {
            helpers.addStyle(currentElement.pill, {
                left: `${closestStep}px`,
                width: `${x + width - closestStep}px`,
            });
        } else {
            helpers.addStyle(currentElement.pill, {
                left: `${x}px`,
                width: `${closestStep - x + currentElementRect.width}px`,
            });
        }

        const direction = currentElement.isStart ? "start" : "end";
        const parentPill = currentElement.closest(pillSelector);
        const diff =
        currentElement.steps.indexOf(closestStep) - currentElement.steps.indexOf(currentElement.initialStep);

        helpers.execHandler("onDrag", { pill: parentPill, direction, diff });
    },
    onDragEnd({ ctx, helpers }) {
        const { currentElement, pillSelector } = ctx;
        const parentPill = currentElement.closest(pillSelector);
        helpers.execHandler("onDragEnd", { pill: parentPill });
    },
    onDrop({ ctx, helpers }) {
        const { currentElement, mouse, pillSelector } = ctx;
        const parentPill = currentElement.closest(pillSelector);
        const closestStep = closest(mouse.x, currentElement.steps);

        if (closestStep === currentElement.initialStep) {
            return;
        }

        const direction = currentElement.isStart ? "start" : "end";
        let diff = currentElement.steps.indexOf(closestStep) - currentElement.steps.indexOf(currentElement.initialStep);
        if (currentElement.isStart) {
            diff *= -1;
        }

        helpers.execHandler("onDrop", { pill: parentPill, diff, direction });
    },
});
