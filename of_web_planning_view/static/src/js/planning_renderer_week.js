/** @odoo-module **/

import { PlanningRenderer } from "./planning_renderer";
import { PlanningCellButtons } from "./planning_cell_buttons";
import { PlanningPopover } from "./popover/planning_popover";
import { PlanningRowProgressBar } from "./planning_row_progress_bar";


export class PlanningWeekRenderer extends PlanningRenderer {
    static components = { PlanningCellButtons,  Popover: PlanningPopover, PlanningRowProgressBar };
    static template = "of_web_planning_view.PlanningWeekRenderer";

    /**
     * @returns {number}
     */
    get pillHeight() {
        return this.constructor.GRID_ROW_HEIGHT_WEEK * this.constructor.ROW_SPAN;
    }

    /**
     * @returns {number}
     */
    get rowHeight() {
        return this.constructor.GRID_ROW_HEIGHT_WEEK;
    }
}

PlanningRenderer.components = {
    ...PlanningRenderer.components,
    PlanningWeekRenderer,
};
