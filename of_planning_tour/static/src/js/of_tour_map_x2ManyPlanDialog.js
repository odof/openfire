/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useRef } from "@odoo/owl";
import { renderToString } from "@web/core/utils/render";
import { OFMapPlanningTourX2Many } from "@of_planning_tour/js/of_tour_map_x2Many";

export class OFMapPlanningTourX2ManyPlanDialog extends OFMapPlanningTourX2Many {
    static template = "of_planning_tour.OFMapPlanningTourPlanDialog";

    setup() {
        super.setup();
        this.mapContainerRef = useRef("mapContainerPlanDialog");
    }

    /**
     * Adds service request's lat and lng to the initial latlngs to ensure it will be visible on the map
     * **/
    getInitialLatLngs() {
        const tabLatLng = super.getInitialLatLngs();
        if (this.props.record?.data?.geo_lat && this.props.record?.data?.geo_lng) {
            tabLatLng.push(L.latLng(
                this.props.record.data.geo_lat,
                this.props.record.data.geo_lng,
            ));
        }
        return tabLatLng
    }

    setMapWidth() {
        /**  This widget is displayed into a grid-template div so we don't want to modify the width and let
         *  the parent container manage the width of the map. **/
    }

    getMarkerIconData(markerInfo, record) {
        const markerIconData = super.getMarkerIconData(markerInfo, record);
        let markerColor;
        if (markerInfo.additional) {
            markerColor = record.is_service_request ? "green" : "black";
        } else {
            markerColor = "blue";
        }

        let markerIcon = "circle";
        if (markerInfo.additional) {
            if (record.is_start_end_marker) {
                markerIcon = "home";
            } else if (record.is_service_request) {
                markerIcon = "wrench";
            }
        }

        return {
            ...markerIconData,
            markerColor,
            icon: markerIcon,
        };
    }

    onClickMarker(record) {
        // We are not using list of popups on this widget, so we redefining this method to empty it
    }

    getTooltip(record, additional = false) {
        const context = additional
            ? { record: { ...record } }
            : { record: record.data };
        if (additional && record.date) {
            const date = new Date(record.date);
            const formattedDate = `${date.getDate().toString().padStart(2, '0')}/${
                (date.getMonth() + 1).toString().padStart(2, '0')}/${
                date.getFullYear()} ${date.getHours().toString().padStart(2, '0')}:${
                date.getMinutes().toString().padStart(2, '0')}`;
            context.record.date = formattedDate;
        }
        return renderToString(this.tooltipView, context);
    }

    updateMarkersInfoWithAdditionalRecords(markersInfo, additionalRecords, pinInSamePlace) {
        for (const record of additionalRecords) {
            const lat_long = `${record.geo_lat}-${record.geo_lng}`;
            const key = `${lat_long}`;
            if (key in markersInfo && markersInfo[key].additional) {
                markersInfo[key].record = record;
                markersInfo[key].ids.push(record.id);
            } else {
                const originalMarkerInfo = markersInfo[key];
                pinInSamePlace[lat_long] = ++pinInSamePlace[lat_long] || 0;
                markersInfo[key] = {
                    additional: true,
                    record: record,
                    ids: [record.id],
                    pinInSamePlace: pinInSamePlace[lat_long],
                };
                if (originalMarkerInfo && !originalMarkerInfo.additional && originalMarkerInfo.tour_number) {
                    markersInfo[key].originalTourNumber = originalMarkerInfo.tour_number;
                }
            }
        }
    }
}

registry
    .category("fields")
    .add("of_planning_tour_map_x2many_plan_dialog", OFMapPlanningTourX2ManyPlanDialog);
