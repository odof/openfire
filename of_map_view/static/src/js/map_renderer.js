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
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.mapContainerRef = useRef("mapContainer");
        this.popups = {};
        this.partners = this.props.model.data.partners.records;
        this.map = false;
        this.markers = {};
        this.iconMarker = {};

        onWillUnmount(this.onWillUnmount);

        useEffect(
            () => {
                if (!this.map) {
                    this.map = L.map(this.mapContainerRef.el).setView(
                        [48.056, -2.818],
                        8
                    );
                    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                        center: [39.73, -104.99],
                        minZoom: 5,
                        maxZoom: 19,
                        attribution:
                            '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                    }).addTo(this.map);

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
            () => [this.props.model.data.partners.records]
        );
    }

    switchView(partner_id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Contact",
            views: [[false, "form"]],
            res_model: this.props.model.metaData.resModel,
            res_id: partner_id,
        });
    }

    updateMap() {
        this.removeMarkers();
        this.props.model.data.partners.records.map((partner) => {
            if (partner.partner_latitude && partner.partner_longitude) {
                this.addMarker(partner);
            }
        });
    }

    onClickMarker(partner) {
        this.popups[partner.id].toggle();
    }

    onMouseOverMarker(partner) {
        this.popups[partner.id].highlight();
    }

    onMouseOutMarker(partner) {
        this.popups[partner.id].lowlight();
    }

    addMarker(partner) {
        let markerLocation = new L.LatLng(
            partner.partner_latitude,
            partner.partner_longitude
        );
        let marker = new L.Marker(markerLocation, {icon: this.iconMarker["normal"]});

        // Ajout du tooltip
        const tooltip = L.tooltip({offset: [15, -25]})
            .setLatLng([partner.partner_latitude, partner.partner_longitude])
            .setContent(this.getTooltip(partner));

        marker.bindTooltip(tooltip);

        this.markers[partner.id] = marker;
        this.map.addLayer(marker);

        marker.on({
            mouseup: this.onClickMarker.bind(this, partner),
            tooltipopen: this.onMouseOverMarker.bind(this, partner),
            tooltipclose: this.onMouseOutMarker.bind(this, partner),
        });
    }

    removeMarkers() {
        const self = this;
        Object.keys(this.markers).forEach(function (key, index) {
            self.map.removeLayer(self.markers[key]);
        });
        this.markers = {};
    }

    getTooltip(partner) {
        return renderToString("of_map_view.tooltipRenderer", {partner: partner});
    }

    // supprimer le popup en changement de page
    onWillUnmount() {
        if (this.map) {
            this.map.remove();
        }
    }
}
