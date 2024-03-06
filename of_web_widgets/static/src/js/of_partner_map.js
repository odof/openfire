/** @odoo-module */
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {registry} from "@web/core/registry";
import {
    Component,
    onWillStart,
    useRef,
    useEffect,
    onMounted,
} from "@odoo/owl";
import {loadJS, loadCSS} from "@web/core/assets";

const DEFAULT_MAP_ROWS = 4;
const MAP_ROWS_HEIGHT_MULTIPLICATOR = 20;

export class OFPartnerMap extends Component {
    static template = "of_web_widgets.OFPartnerMap";
    static props = {
        ...standardFieldProps,
        mapRows: {type: Number, optional: true},
        mapRows: {type: Number, optional: true},
    };
    static supportedTypes = ["many2one"];
    static supportedTypes = ["many2one"];
    static extractProps = ({attrs, field}) => {
        return {
            mapRows: attrs.options.map_rows,
        };
    };

    setup() {
        this.mapRows = this.props.mapRows || DEFAULT_MAP_ROWS;
        this.leafletMap = null;
        this.mapContainerRef = useRef("mapContainer");
        this.fitbounds = [];
        this.markers = [];

        onWillStart(async () => {
            await Promise.all([
                loadJS(["/of_web_widgets/static/lib/leaflet/leaflet.js"]),
                loadCSS("/of_web_widgets/static/lib/leaflet/leaflet.css"),
            ]);
        });

        onMounted(() => {
            $(this.mapContainerRef.el).height(
                MAP_ROWS_HEIGHT_MULTIPLICATOR * this.mapRows
            );
            $(this.mapContainerRef.el).width(
                $(this.mapContainerRef.el.parentElement.parentElement).width()
            );
            this.leafletMap = L.map(this.mapContainerRef.el).setView(
                [
                    this.props.record.data.partner_latitude,
                    this.props.record.data.partner_longitude,
                ],
                14
            );
            L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution:
                    '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            }).addTo(this.leafletMap);

            this.addMarker(this.props.record.data);
        });

        useEffect(
            () => {
                this.updateMap();
            },
            () => [this.props.value]
        );
    }

    addMarker(partner, icon = false) {
        let marker = false;
        if (partner.partner_latitude && partner.partner_longitude) {
            if (icon) {
                marker = L.marker(
                    [partner.partner_latitude, partner.partner_longitude],
                    {icon: icon}
                ).addTo(this.leafletMap);
            } else {
                marker = L.marker([
                    partner.partner_latitude,
                    partner.partner_longitude,
                ]).addTo(this.leafletMap);
            }
            marker.bindTooltip(partner.display_name);
            this.markers.push(marker);
            this.fitbounds.push([partner.partner_latitude, partner.partner_longitude]);
            this.leafletMap.fitBounds(this.fitbounds, {padding: [20, 20]});
        }
    }

    updateMap() {
        this.markers.map((marker) => {
            // on supprime tous les markers
            this.leafletMap.removeLayer(marker);
        });
        this.fitbounds = [];
        this.markers = [];
        // on les refait
        this.addMarker(this.props.record.data);
    }

    onWillUnmount() {
        if (this.leafletMap) {
            this.leafletMap.remove();
        }
    }
}

registry.category("fields").add("of_partner_map", OFPartnerMap);
