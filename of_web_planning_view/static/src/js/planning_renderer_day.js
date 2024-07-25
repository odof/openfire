/** @odoo-module **/

import { PlanningRenderer } from "./planning_renderer";
import { PlanningCellButtons } from "./planning_cell_buttons";
import { PlanningPopover } from "./popover/planning_popover";
import { PlanningRowProgressBar } from "./planning_row_progress_bar";
import { dateAddFixedOffset } from "./planning_helpers";

const { DateTime } = luxon;

export class PlanningDayRenderer extends PlanningRenderer {

    static template = "of_web_planning_view.PlanningDayRenderer";
    static headerTemplate = "of_web_planning_view.PlanningDayRenderer.Header";
    static rowContentTemplate = "of_web_planning_view.PlanningDayRenderer.RowContent";
    static pillTemplate = "of_web_planning_view.PlanningDayRenderer.Pill";
    static components = {PlanningCellButtons, Popover: PlanningPopover, PlanningRowProgressBar};

    onMounted() {
        // Center the view on today
        const selectedItems = document.querySelectorAll(".o_planning_header_cell.o_planning_today");
        const selectedItem = selectedItems[Math.floor(selectedItems.length / 2)];
        if (selectedItem) {
            selectedItem.scrollIntoView({ behavior: "smooth", inline: "center" });
        }
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
        const start_hour = this.model.start_hour;
        const end_hour = this.model.end_hour;
        let previousDate;
        for (date = startDate; date <= stopDate; date = date.plus({ 'minute': 5 })) {
            const start = date;
            if (start.c.hour < start_hour || start.c.hour > end_hour) {
                continue;
            }
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
            const isNow = date.hasSame(now, "day") && date.hasSame(now, "hour") && date.c.minute <= now.c.minute && now.c.minute < (date.c.minute + 5);
            const dayChanged = previousDate && previousDate.c.day != date.c.day;

            if (isToday) {
                column.isToday = true;
            }
            if (isNow) {
                column.isNow = true;
            }
            if (dayChanged) {
                column.dayChanged = true;
            }

            this.columns.push(column);

            for (let i = 0; i < cellPart; i++) {
                const subCellStart = dateAddFixedOffset(start, { [time]: i * cellTime });
                const subCellStop = dateAddFixedOffset(start, {
                    [time]: (i + 1) * cellTime,
                    seconds: -1,
                });
                this.subColumns.push({ start: subCellStart, stop: subCellStop, isToday, isNow, dayChanged, columnId });
                this.dateGridColumns.push(subCellStart);
            }

            colOffset += cellPart;
            previousDate = date;
        }

        this.dateGridColumns.push(date);
    }

    /**
     * @param {{ column?: number | number[], row?: number | number[] }} position
     */
    getButtonPosition(position, span) {
        const style = [];
        for (const prop of ["column", "row"]) {
            const [index, span] = Array.isArray(position[prop]) ? position[prop] : [position[prop]];
            if (prop == 'column' && span && span == 1) {
                style.push(`grid-${prop}:${index} / span 12`);
            }
            else if (span && span !== 1) {
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
        const start_hour = this.model.start_hour;
        const end_hour = this.model.end_hour;

        let start, stop;
        let date;
        let absDiff = Math.abs(diff);
        let sign = Math.sign(diff);
        if (sign) {
            for (date = record[dateStartField]; absDiff != 0; date = date.plus({ 'minute': sign * 5 })) {
                if (date.c.hour < start_hour || date.c.hour > end_hour) {
                    diff = diff + sign;
                    continue;
                }
                absDiff--;
            }

        }
        start = diff && dateAddFixedOffset(record[dateStartField], { [time]: cellTime * diff / 12 });
        stop = diff && dateAddFixedOffset(record[dateStopField], { [time]: cellTime * diff / 12 });

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
     * @param {Object} params
     * @param {Element} params.pill
     * @param {number} params.diff
     * @param {"start" | "end"} params.direction
     */
    async resizePillDrop({ pill, diff, direction }) {
        const { dateStartField, dateStopField, durationField, scale } = this.model.metaData;
        const { cellTime, time } = scale;
        const { record } = this.pills[pill.dataset.pillId];
        const params = {};
        const start_hour = this.model.start_hour;
        const end_hour = this.model.end_hour;

        let date;
        let absDiff = Math.abs(diff);
        let sign = Math.sign(diff);
        if (sign) {
            for (date = direction === "start" ? record[dateStartField] : record[dateStopField]; absDiff != 0; date = date.plus({ 'minute': sign * 5 })) {
                if (date.c.hour < start_hour || date.c.hour > end_hour) {
                    diff = diff + sign;
                    continue;
                }
                absDiff--;
            }
        }

        if (direction === "start") {
            params.start = dateAddFixedOffset(record[dateStartField], { ['minute']: 5 * diff });
            // On rajoute également la nouvelle durée car sinon la date de fin est recalculée.
            // Ce qui décalerait l'intervention au lieu da la resizer
            params.duration = record[durationField] - ((5 * diff)/60);
        } else {
            // (diff + 1) pour compenser certaines imprécisions du resize
            params.stop = dateAddFixedOffset(record[dateStopField], { ['minute']: 5 * (diff + 1) });
        }
        const schedule = this.model.getSchedule(params);

        await this.model.reschedule(record.id, schedule, this.openPlanDialogCallback);
    }
}


PlanningRenderer.components = {
    ...PlanningRenderer.components,
    PlanningDayRenderer,
};
