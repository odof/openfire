/** @odoo-module **/

import { Component, useEffect, useRef } from "@odoo/owl";

export class PlanningCellButtons extends Component {
    static props = {
        reactive: {
            type: Object,
            shape: {
                cell: [HTMLElement, { value: null }],
                // Only for day scale because we don't want to rerender buttons on each cell change on day View
                dayCell: [HTMLElement, { value: null }],
            },
        },
        canCreate: Boolean,
        canPlan: Boolean,
        onCreate: Function,
        onPlan: Function,
        scale: Object,
    };
    static template = "of_web_planning_view.PlanningCellButtons";

    onCreate() {
        this.props.onCreate(this.props.reactive.cell.dataset);
    }

    onPlan() {
        this.props.onPlan(this.props.reactive.cell.dataset)
    }
}
