/** @odoo-module */

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { renderToString } from "@web/core/utils/render";
import { Component, useRef, useEffect, onWillStart, onWillUnmount } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";
import { ListPopupMap } from "@of_web_widgets/components/popup";

const DEFAULT_MAP_ROWS = 4;
const MAP_ROWS_HEIGHT_MULTIPLICATOR = 20;
const MAP_VIEW_ZOOM = 14;
const DEFAULT_POLYLINE_COLOR = "#0066cc";
const DEFAULT_TOUR_START_STOP_COLOR = "#333333";
const DEFAULT_ADDITIONNAL_RECORD_COLOR = "#25aa22";
const DEFAULT_POLYLINE_OPACITY = 0.8;
const DEFAULT_POLYLINE_WEIGHT = 3;
const SELECTED_POLYLINE_WEIGHT = 5;
const SELECTED_POLYLINE_OPACITY = 1.0;

export class OFMapPlanningTourX2Many extends Component {
    static template = "of_planning_tour.OFMapPlanningTour";
    static supportedTypes = ["one2many", "many2many"];
    static components = {
        ListPopupMap,
    };

    static props = {
        ...standardFieldProps,
        mapRows: { type: Number, optional: true },
        width: { type: Number, optional: true },
        minWidth: { type: Number, optional: true },
        height: { type: Number, optional: true },
        minHeight: { type: Number, optional: true },
    };

    static extractProps = ({ attrs, field }) => {
        return {
            mapRows: attrs.options.map_rows || DEFAULT_MAP_ROWS,
            width: attrs.options.width || 0,
            height: attrs.options.height || 0,
            minWidth: attrs.options.min_width || 0,
            minHeight: attrs.options.min_height || 0,
        };
    };

    setup() {
        this.mapRows = this.props.mapRows || DEFAULT_MAP_ROWS;
        this.width = this.props.width || null;
        this.height = this.props.height || null;
        this.minWidth = this.props.minWidth || null;
        this.minHeight = this.props.minHeight || null;
        this.map = null;
        this.mapContainerRef = useRef("mapContainer");
        this.fitbounds = [];
        this.archInfo = {
            fromWidget: true,
            width: null, // that is width of popup detail, it will be calculated in onMounted() hook
            popoverTemplate: "of_planning_tour.popoverMarker",
        };
        this.tooltipView = "of_planning_tour.tooltipMarker";
        this.markers = {};
        this.polylines = [];
        this.additionalPolylines = [];
        this.startLatLng = null;
        this.returnLatLng = null;
        this.popups = {};

        onWillStart(this.loadDependencies.bind(this));
        useEffect(this.initializeMap.bind(this), () => [this.props.value]);
        onWillUnmount(this.cleanUpMap.bind(this));
    }

    /** Getter **/

    get records() {
        return this.props.value.records || [];
    }

    /** Methods **/

    async loadDependencies() {
        await Promise.all([
            await loadCSS("/of_web_widgets/static/lib/leaflet/leaflet.css"),
            await loadJS("/of_web_widgets/static/lib/leaflet/leaflet.js"),
            await loadCSS(
                "/of_web_widgets/static/lib/awesome-markers/leaflet.awesome-markers.css"
            ),
            await loadJS(
                "/of_web_widgets/static/lib/awesome-markers/leaflet.awesome-markers.js"
            ),
        ]);

        const { start_address_id, return_address_id, company_id } = this.props.record.data;
        if (start_address_id && return_address_id) {
            const partnerData = await this.props.record.model.orm.read(
                "res.partner",
                [start_address_id[0], return_address_id[0]],
                ["partner_latitude", "partner_longitude"]
            );
            this.startLatLng = partnerData ? partnerData[0] : null;
            this.returnLatLng = partnerData ? partnerData[1] : null;
        } else if (company_id) {  // If no start and return address, we use the company address as start and return...
            const partnerData = await this.props.record.model.orm.read(
                "res.partner",
                [company_id[0], company_id[0]],
                ["partner_latitude", "partner_longitude"]
            );
            this.startLatLng = partnerData ? partnerData[0] : null;
            this.returnLatLng = partnerData ? partnerData[1] : null;
        }
    }

    initializeMap() {
        if (!this.map) {
            this.setMap();
            this.setListPopupWidth();
        }
        this.updateMap();
    }

    cleanUpMap() {
        this.removeMarkers();
        this.removeRoutes();
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }

    getMapViewParams() {
        return {
            map_zoom: MAP_VIEW_ZOOM,
            map_latitude: this.props.record.data.map_latitude,
            map_longitude: this.props.record.data.map_longitude,
        };
    }

    setMapWidth() {
        $(this.mapContainerRef.el).width(
            $(this.mapContainerRef.el.parentElement.parentElement.parentElement).width()
        );
    }

    setMapHeight() {
        $(this.mapContainerRef.el).height(MAP_ROWS_HEIGHT_MULTIPLICATOR * this.mapRows);
    }

    setMap() {
        this.setMapWidth();
        this.setMapHeight();
        const { map_latitude, map_longitude, map_zoom } = this.getMapViewParams();
        this.map = L.map(this.mapContainerRef.el).setView(
            [map_latitude, map_longitude],
            map_zoom
        );
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution:
                '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        }).addTo(this.map);
    }

    setListPopupWidth() {
        this.archInfo.width = $(this.mapContainerRef.el).width() / 6;
    }

    updateMap() {
        this.closePopups();
        this.removePopups();

        const initialLatLngs = this.getInitialLatLngs();
        const initialCoord = L.latLngBounds(initialLatLngs);
        if (initialCoord) {
            this.map.flyToBounds(initialCoord, { animate: false });
        } else {
            this.map.fitWorld();
        }
        this.addMarkers();
        this.addRoutes();
    }

    /**
     *
     * Add markers on the map.
     * Markers are displayed on the map at the location of events.
     * Each marker is clickable and displays a tooltip with information about the event.
     *
     * There is also additional markers that are displayed on the map, they represent the start and end of the tour.
     * Used by Tour views.
     *
     */
    addMarkers() {
        this.removeMarkers();
        const { records } = this;
        const additionalRecords = JSON.parse(this.props.record.data.additional_records);

        if (additionalRecords.length) {

            // Build markers info object to group markers that are in the same place
            const markersInfo = {};
            const pinInSamePlace = {};
            // Update markersInfo with classic records and additional records
            this.updateMarkersInfoWithClassicRecords(markersInfo, records, pinInSamePlace);
            this.updateMarkersInfoWithAdditionalRecords(markersInfo, additionalRecords, pinInSamePlace);

            // For each marker info, create a marker and add it to the map
            for (const markerInfo of Object.values(markersInfo)) {
                const offset = markerInfo.pinInSamePlace * 0.000025;
                const { record } = markerInfo;

                // Additional markers are fake records that are not persisted in the database
                // (eg. start and end of the tour)
                const markerLat = markerInfo.additional
                    ? record.geo_lat
                    : record.data.geo_lat;
                const markerLng = markerInfo.additional
                    ? record.geo_lng
                    : record.data.geo_lng;
                let markerLocation = new L.LatLng(markerLat + offset, markerLng - offset);

                const markerIconData = this.getMarkerIconData(markerInfo, record);

                let marker = new L.Marker(markerLocation, {
                    icon: L.AwesomeMarkers.icon(markerIconData),
                });

                const tooltip = L.tooltip({ offset: [15, -25] })
                    .setLatLng([markerLat, markerLng])
                    .setContent(this.getTooltip(record, markerInfo.additional));

                marker.bindTooltip(tooltip);

                // Adding marker to Object array that will used for tooltip open/close events
                this.markers[record.id] = marker;

                // Adding marker to the map
                this.map.addLayer(marker);

                marker.on({
                    mouseup: this.onClickMarker.bind(this, record),
                    tooltipopen: this.onMouseOverMarker.bind(this, record),
                    tooltipclose: this.onMouseOutMarker.bind(this, record),
                });
            }
        }
    }


    /**
     * Updates the markers information with classic records.
     *
     * @param {Object} markersInfo - The current markers information.
     * @param {Array} records - The array of records to update the markers information with.
     * @param {Object} pinInSamePlace - The object that keeps track of pins in the same place.
     */
    updateMarkersInfoWithClassicRecords(markersInfo, records, pinInSamePlace) {
        for (const record of records) {
            const { data } = record;
            if (data && data.geo_lat && data.geo_lng) {
                const lat_long = `${data.geo_lat}-${data.geo_lng}`;
                const key = `${lat_long}`;
                if (key in markersInfo) {
                    markersInfo[key].record = record;
                    markersInfo[key].ids.push(record.id);
                } else {
                    pinInSamePlace[lat_long] = ++pinInSamePlace[lat_long] || 0;
                    markersInfo[key] = {
                        additional: false,
                        record: record,
                        ids: [record.id],
                        pinInSamePlace: pinInSamePlace[lat_long],
                        tour_number: data.tour_number,
                    };
                }
            }
        }
    }

    /**
     * Updates the markers information with additional records.
     *
     * @param {Object} markersInfo - The existing markers information.
     * @param {Array} additionalRecords - The additional records to be added.
     * @param {Object} pinInSamePlace - The object to store the count of pins in the same place.
     */
    updateMarkersInfoWithAdditionalRecords(markersInfo, additionalRecords, pinInSamePlace) {
        for (const record of additionalRecords) {
            const lat_long = `${record.geo_lat}-${record.geo_lng}`;
            const key = `${lat_long}`;
            if (key in markersInfo) {
                markersInfo[key].additional = true;
                markersInfo[key].record = record;
                markersInfo[key].ids.push(record.id);
            } else {
                pinInSamePlace[lat_long] = ++pinInSamePlace[lat_long] || 0;
                markersInfo[key] = {
                    additional: true,
                    record: record,
                    ids: [record.id],
                    pinInSamePlace: pinInSamePlace[lat_long],
                };
            }
        }
    }

    /**
     * Add routes on the map.
     * **/
    addRoutes() {
        this.removeRoutes();
        this.drawRoutesFromRecords();
        this.drawRoutesFromFakeRecords();
    }

    /**
     * Get initial coordinates of the map to set the view centered on the tour.
     *
     * Retrieves the initial latitude and longitude values for the tour map.
     * @returns {Array} An array of LatLng objects representing the initial latitude and longitude values.
     */
    getInitialLatLngs() {
        const tabLatLng = [];
        tabLatLng.push(
            L.latLng(
                this.startLatLng.partner_latitude,
                this.startLatLng.partner_longitude
            )
        );
        for (const line of this.getLinesData()) {
            if (line && line.geo_lat && line.geo_lng) {
                tabLatLng.push(L.latLng(line.geo_lat, line.geo_lng));
            }
        }
        tabLatLng.push(
            L.latLng(
                this.returnLatLng.partner_latitude,
                this.returnLatLng.partner_longitude
            )
        );
        return tabLatLng;
    }

    getTooltip(record, additional = false) {
        const context = additional
            ? { record: { tour_number: record.tour_number,
                partner_name : record.partner_name,
                of_address_zip: record.address_zip,
                of_address_city: record.address_city,
            }
        }
            : { record: record.data };
        return renderToString(this.tooltipView, context);
    }

    getLinesData() {
        const tourLines = [];
        if (this.records === undefined || this.records.length === 0) {
            return tourLines;
        }
        for (const record of this.records) {
            if (record && record.data) {
                tourLines.push(record.data);
            }
        }
        return tourLines;
    }

    /**
     * Draws routes from records on the map.
     */
    drawRoutesFromRecords() {
        for (const record of this.getLinesData()) {
            if (record.geometry_data) {
                let geometry = JSON.parse(record.geometry_data);
                if (!geometry || geometry.length < 2) {
                    continue;
                }
                let lineColor = record.hexa_color || DEFAULT_POLYLINE_COLOR;

                if (record.is_first_line_of_tour) {
                    lineColor = DEFAULT_TOUR_START_STOP_COLOR;
                }

                const latLngs = [];
                for (const step of geometry) {
                    for (const coordinate of step.coordinates) {
                        latLngs.push(L.latLng(coordinate[1], coordinate[0]));
                    }
                }

                let polyline = L.polyline([...latLngs], {
                    color: lineColor,
                    weight: DEFAULT_POLYLINE_WEIGHT,
                    opacity: DEFAULT_POLYLINE_OPACITY,
                    smoothFactor: 1,
                }).addTo(this.map);

                let endpointLatLngs = [];
                if (record.is_last_line_of_tour && record.endpoint_geometry_data) {
                    let endpointGeometry = JSON.parse(record.endpoint_geometry_data);
                    if (endpointGeometry && endpointGeometry.length > 0) {
                        for (const step of endpointGeometry) {
                            for (const coordinate of step.coordinates) {
                                endpointLatLngs.push(
                                    L.latLng(coordinate[1], coordinate[0])
                                );
                            }
                        }
                    }
                }
                let polylineEnd = L.polyline([...endpointLatLngs], {
                    color: DEFAULT_TOUR_START_STOP_COLOR,
                    weight: DEFAULT_POLYLINE_WEIGHT,
                    opacity: DEFAULT_POLYLINE_OPACITY,
                    smoothFactor: 1,
                }).addTo(this.map);

                const { polylines } = this;
                polyline.on("click", function () {
                    for (const polyline of polylines) {
                        polyline.setStyle({
                            opacity: DEFAULT_POLYLINE_OPACITY,
                            weight: DEFAULT_POLYLINE_WEIGHT,
                        });
                    }
                    this.setStyle({
                        opacity: SELECTED_POLYLINE_OPACITY,
                        weight: SELECTED_POLYLINE_WEIGHT,
                    });
                });
                polylineEnd.on("click", function () {
                    for (const polyline of polylines) {
                        polyline.setStyle({
                            opacity: DEFAULT_POLYLINE_OPACITY,
                            weight: DEFAULT_POLYLINE_WEIGHT,
                        });
                    }
                    this.setStyle({
                        opacity: SELECTED_POLYLINE_OPACITY,
                        weight: SELECTED_POLYLINE_WEIGHT,
                    });
                });
                this.polylines.push(polyline);
                this.polylines.push(polylineEnd);
            }
        }
    }

    getMarkerIconData(markerInfo, record) {
        let markerColor = markerInfo.additional ? "black" : "blue";
        let markerIcon = markerInfo.additional ? "home" : "circle";
        let markerNumber = markerInfo.additional ? null : record.data.tour_number;

        let isMulti = markerNumber && typeof markerNumber === "string" && markerNumber.split(',').length > 1 || false;
        if (isMulti) {
            markerNumber = `${markerNumber.split(',')[0]}...`;
        }

        return {
            icon: markerIcon,
            markerColor: markerColor,
            text: markerNumber,
        };
    }

    /**
     * Draws routes from fake records.
     *
     * Fake records are additional records that are not persisted in the database at the moment of the map rendering.
     * They are used to display the start and end of the tour, and the service requests to be planned.
     *
     */
    drawRoutesFromFakeRecords() {
        const {additional_record_geometry_data} = this.props.record.data;
        let fakeRecordsLatLngs = [];
        if (additional_record_geometry_data) {
            let fakeRecordGeometry = JSON.parse(additional_record_geometry_data);
            if (fakeRecordGeometry && fakeRecordGeometry.length > 0) {
                for (const step of fakeRecordGeometry) {
                    for (const coordinate of step.coordinates) {
                        fakeRecordsLatLngs.push(
                            L.latLng(coordinate[1], coordinate[0])
                        );
                    }
                }
            }
        }
        let polyline = L.polyline([...fakeRecordsLatLngs], {
            color: DEFAULT_ADDITIONNAL_RECORD_COLOR,
            weight: DEFAULT_POLYLINE_WEIGHT,
            opacity: DEFAULT_POLYLINE_OPACITY,
            smoothFactor: 1,
        }).addTo(this.map);
        this.additionalPolylines.push(polyline);
    }

    /**
     * Remove markers from the map.
     */
    removeMarkers() {
        const arrayOfMarkers = Object.values(this.markers);
        for (const marker of arrayOfMarkers) {
            marker.off("click");
            this.map.removeLayer(marker);
        }
        this.markers = {};
    }

    /**
     * Remove routes from the map.
     */
    removeRoutes() {
        for (const polyline of this.polylines) {
            polyline.off("click");
            this.map.removeLayer(polyline);
        }
        for (const polyline of this.additionalPolylines) {
            polyline.off("click");
            this.map.removeLayer(polyline);
        }
        this.polylines = [];
        this.additionalPolylines = [];
    }

    removePopups() {
        this.popups = {};
    }

    /**
     * Close all popups.
     */
    closePopups() {
        for (let index = 0; index < Object.keys(this.popups).length; index++) {
            this.popups[Object.keys(this.popups)[index]].state.show = false;
        }
    }

    /** Events **/

    onClickMarker(record) {
        // Fake records likes Start/Stop markers are not available in `popups` object as its
        // initialized with `map.model.root.records`.
        if (record.id in this.popups){
            this.popups[record.id].toggle();
            record.selected = !record.selected;
        }
    }

    onMouseOverMarker(record) {
        if (this.popups[record.id]) {
            this.popups[record.id].highlight();
        }
    }

    onMouseOutMarker(record) {
        if (this.popups[record.id]) {
            this.popups[record.id].lowlight();
        }
    }
}

registry.category("fields").add("of_planning_tour_map_x2many", OFMapPlanningTourX2Many);
