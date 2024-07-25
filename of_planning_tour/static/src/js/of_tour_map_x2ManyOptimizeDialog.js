/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useRef } from "@odoo/owl";
import { OFMapPlanningTourX2ManyPlanDialog } from "@of_planning_tour/js/of_tour_map_x2ManyPlanDialog";

export class OFMapPlanningTourX2ManyOptimizeDialog extends OFMapPlanningTourX2ManyPlanDialog {
    static template = "of_planning_tour.OFMapPlanningTourOptimizeDialog";

    setup() {
        super.setup();
        this.mapContainerRef = useRef("mapContainerOptimizeDialog");
    }

    setMapWidth() {
        /**  This widget is displayed into a grid-template div so we don't want to modify the width and let
         *  the parent container manage the width of the map. **/
    }
}

registry
    .category("fields")
    .add("of_planning_tour_map_x2many_optz_dialog", OFMapPlanningTourX2ManyOptimizeDialog);
