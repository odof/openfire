/** @odoo-module */

import {OFPartnerMap} from "@of_web_widgets/js/of_partner_map";
import {registry} from "@web/core/registry";
import {onMounted, onPatched} from "@odoo/owl";

export class OFMapGeolocalize extends OFPartnerMap {
    setup() {
        super.setup();

        onMounted(async () => {
            // on va chercher les enfants et la société parente si elle existe
            await this.loadChilds();
            await this.loadParent();
        });

        onPatched(async () => {
            await this.loadChilds();
            await this.loadParent();
        });
    }

    async loadChilds() {
        const iconChild = L.icon({
            iconUrl: "/of_web_widgets/static/lib/leaflet/images/marker-icon-black.png",
            shadowUrl: "/of_web_widgets/static/lib/leaflet/images/marker-shadow.png",
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            tooltipAnchor: [16, -28],
            shadowSize: [41, 41],
        });

        let childs = await this.props.record.model.orm.searchRead(
            "res.partner",
            [["parent_id", "=", this.props.record.data.id]],
            ["id", "partner_latitude", "partner_longitude", "display_name"]
        );
        childs.map((child) => {
            this.addMarker(child, iconChild);
        });
    }

    async loadParent() {
        const iconParent = L.icon({
            iconUrl: "/of_web_widgets/static/lib/leaflet/images/marker-icon-green.png",
            shadowUrl: "/of_web_widgets/static/lib/leaflet/images/marker-shadow.png",
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            tooltipAnchor: [16, -28],
            shadowSize: [41, 41],
        });

        if (this.props.record.data.parent_id) {
            let parent = await this.props.record.model.orm.searchRead(
                "res.partner",
                [["id", "=", this.props.record.data.parent_id[0]]],
                ["id", "partner_latitude", "partner_longitude", "display_name"]
            );
            if (parent.length == 1) {
                this.addMarker(parent[0], iconParent);
            }
        }
    }
}

registry.category("fields").add("of_geolocalize_map", OFMapGeolocalize);
