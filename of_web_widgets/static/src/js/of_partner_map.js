/** @odoo-module */
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { Component, onWillStart, useRef, useEffect, onMounted } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";

const DEFAULT_MAP_ROWS = 4;
const MAP_ROWS_HEIGHT_MULTIPLICATOR = 20;
const MAP_VIEW_ZOOM = 14;

export class OFPartnerMap extends Component {
    static template = "of_web_widgets.OFPartnerMap";
    static props = {
        ...standardFieldProps,
        mapRows: { type: Number, optional: true },
    };
    static supportedTypes = ["many2one"];
    static extractProps = ({ attrs, field }) => {
        return {
            mapRows: attrs.options.map_rows,
        };
    };

    setup() {
        this.mapRows = this.props.mapRows || DEFAULT_MAP_ROWS;
        this.map = null;
        this.mapContainerRef = useRef("mapContainer");
        this.fitbounds = [];
        this.markers = [];

        onWillStart(async () => {
            // Loading leaflet
            await Promise.all([
                await loadCSS("/of_web_widgets/static/lib/leaflet/leaflet.css"),
                await loadJS(["/of_web_widgets/static/lib/leaflet/leaflet.js"]),
            ]);
            // Loading awesome markers
            await Promise.all([
                await loadCSS(
                    "/of_web_widgets/static/lib/awesome-markers/leaflet.awesome-markers.css"
                ),
                await loadJS([
                    "/of_web_widgets/static/lib/awesome-markers/leaflet.awesome-markers.js",
                ]),
            ]);
        });

        onMounted(this.onMounted);

        useEffect(
            () => {
                this.updateMap();
            },
            () => [this.props.value]
        );
    }

    onMounted() {
        this.setMap();
        this.addMarker(this.props.record.data);
    }

    getMapViewParams() {
        return {
            map_latitude: this.props.record.data.partner_latitude,
            map_longitude: this.props.record.data.partner_longitude,
            map_zoom: MAP_VIEW_ZOOM,
        };
    }

    setMap() {
        $(this.mapContainerRef.el).height(MAP_ROWS_HEIGHT_MULTIPLICATOR * this.mapRows);
        $(this.mapContainerRef.el).width(
            $(this.mapContainerRef.el.parentElement.parentElement).width()
        );
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

    addMarker(partner, icon = false) {
        let marker = false;
        if (partner.partner_latitude && partner.partner_longitude) {
            if (icon) {
                marker = L.marker(
                    [partner.partner_latitude, partner.partner_longitude],
                    { icon: icon }
                ).addTo(this.map);
            } else {
                marker = L.marker([
                    partner.partner_latitude,
                    partner.partner_longitude,
                ]).addTo(this.map);
            }
            marker.bindTooltip(partner.display_name);
            this.markers.push(marker);
            this.fitbounds.push([partner.partner_latitude, partner.partner_longitude]);
            this.map.fitBounds(this.fitbounds, { padding: [20, 20] });
        }
    }

    updateMap() {
        this.markers.map((marker) => {
            // on supprime tous les markers
            this.map.removeLayer(marker);
        });
        this.fitbounds = [];
        this.markers = [];
        // on les refait
        this.addMarker(this.props.record.data);
    }

    onWillUnmount() {
        if (this.map) {
            this.map.remove();
        }
    }
}

registry.category("fields").add("of_partner_map", OFPartnerMap);
