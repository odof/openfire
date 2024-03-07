/** @odoo-module */

import {Component, useEffect, onWillUnmount, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {renderToString} from "@web/core/utils/render";
import {ListPopupMap} from "../components/popup";

export class MapRenderer extends Component {
    static template = "of_map_view.MapRenderer";

    static components = {
        ListPopupMap,
    };

    setup() {
        this.model = this.props.model;
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.mapContainerRef = useRef("mapContainer");
        this.popups = {};
        this.records = this.props.model.data.records.records;
        this.map = false;
        this.markers = {};
        this.iconMarker = {};

        onWillUnmount(this.onWillUnmount);

        useEffect(
            () => {
                const {latitudeField, longitudeField} = this.model.metaData;

                if (!this.map) {
                    this.map = L.map(this.mapContainerRef.el).setView(
                        [48.056, -2.818],
                        8
                    );
                    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                        center: [39.73, -104.99],
                        attribution:
                            '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                    }).addTo(this.map);

                    let arrayOfMarkers = [];
                    this.records.map((record) => {
                        if (record[latitudeField] && record[longitudeField]) {
                            arrayOfMarkers.push([
                                record[latitudeField],
                                record[longitudeField],
                            ]);
                        }
                    });

                    if (arrayOfMarkers.length) {
                        const bounds = new L.LatLngBounds(arrayOfMarkers);
                        this.map.fitBounds(bounds);
                    }

                    // chargement des types d'icones
                    this.iconMarker["normal"] = L.AwesomeMarkers.icon({
                        icon: "circle",
                        markerColor: "blue",
                    });

                    this.iconMarker["highlight"] = L.AwesomeMarkers.icon({
                        icon: "circle",
                        markerColor: "red",
                    });

                    this.iconMarker["selected"] = L.AwesomeMarkers.icon({
                        icon: "check-circle",
                        markerColor: "blue",
                    });

                    this.iconMarker["highlight-selected"] = L.AwesomeMarkers.icon({
                        icon: "check-circle",
                        markerColor: "red",
                    });
                }

                this.updateMap();
            },
            () => [this.props.model.data.records.records]
        );
    }

    switchView(record_id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Contact",
            views: [[false, "form"]],
            res_model: this.props.model.metaData.resModel,
            res_id: record_id,
        });
    }

    updateMap() {
        const {latitudeField, longitudeField} = this.model.metaData;

        this.removeMarkers();
        this.closePopups();
        let arrayOfMarkers = [];
        this.props.model.data.records.records.map((record) => {
            if (record[latitudeField] && record[longitudeField]) {
                this.addMarker(record);
                arrayOfMarkers.push([record[latitudeField], record[longitudeField]]);
            }
        });

        if (arrayOfMarkers.length) {
            const bounds = new L.LatLngBounds(arrayOfMarkers);
            this.map.fitBounds(bounds);
        }
    }

    onClickMarker(record) {
        this.popups[record.id].toggle();
    }

    onMouseOverMarker(record) {
        this.popups[record.id].highlight();
    }

    onMouseOutMarker(record) {
        this.popups[record.id].lowlight();
    }

    addMarker(record) {
        const {latitudeField, longitudeField} = this.model.metaData;

        let markerLocation = new L.LatLng(
            record[latitudeField],
            record[longitudeField]
        );
        let marker = new L.Marker(markerLocation, {icon: this.iconMarker["normal"]});

        // Ajout du tooltip
        const tooltip = L.tooltip({offset: [15, -25]})
            .setLatLng([record[latitudeField], record[longitudeField]])
            .setContent(this.getTooltip(record));

        marker.bindTooltip(tooltip);

        this.markers[record.id] = marker;
        this.map.addLayer(marker);

        marker.on({
            mouseup: this.onClickMarker.bind(this, record),
            tooltipopen: this.onMouseOverMarker.bind(this, record),
            tooltipclose: this.onMouseOutMarker.bind(this, record),
        });
    }

    removeMarkers() {
        const self = this;
        Object.keys(this.markers).forEach(function (key, index) {
            self.map.removeLayer(self.markers[key]);
        });
        this.markers = {};
    }

    closePopups() {
        for (let index = 0; index < Object.keys(this.popups).length; index++) {
            this.popups[Object.keys(this.popups)[index]].state.show = false;
        }
    }

    getTooltip(record) {
        const {tooltipView} = this.model.metaData;
        return renderToString(tooltipView, {record: record});
    }

    // supprimer le popup en changement de page
    onWillUnmount() {
        if (this.map) {
            this.map.remove();
        }
    }
}
