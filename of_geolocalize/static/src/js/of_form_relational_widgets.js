odoo.define('of_geolocalize.of_form_relational_widgets', function (require) {
"use strict";

var Model = require('web.DataModel');
var core = require('web.core');
var _t = core._t;

var FieldMany2One = core.form_widget_registry.get('many2one');

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

/**
    This widget is intended to display a warning near a label of a 'res.partner' many2one field
    indicating if the partner is not geolocalized.
    This widget depends on 3 fields given with params 'geo_lat_field', 'geo_lng_field', 'geocoding_field'.
*/
FieldMany2One.include({
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.dfd_geo_values = $.Deferred()
    },
    initialize_content: function() {
        var self = this;
        this._super.apply(this, arguments);

        if (this.field.relation == 'res.partner') {
            this.geo_lat_field = (this.options && this.options.geo_lat_field) || this.geo_lat_field || 'geo_lat';
            this.geo_lng_field = (this.options && this.options.geo_lng_field) || this.geo_lng_field || 'geo_lng';
            this.geocoding_field = (this.options && this.options.geocoding_field) || this.geocoding_field || 'geocoding'
            if (this.has_geo_fields()) {
                this.set({"geo_lat": this.field_manager.get_field_value(this.geo_lat_field)});
                this.set({"geo_lng": this.field_manager.get_field_value(this.geo_lng_field)});
                this.set({"geocoding": this.field_manager.get_field_value(this.geocoding_field)});
                console.log("on passe par ici ?", this.field_manager.get_field_value(this.geo_lat_field));
            }else{
                this.set_geo_values();
            }
        }
    },
    has_geo_fields: function () {
        return !isNullOrUndef(this.field_manager.fields)
            && !isNullOrUndef(this.field_manager.fields[this.geo_lat_field])
            && !isNullOrUndef(this.field_manager.fields[this.geo_lng_field])
            && !isNullOrUndef(this.field_manager.fields[this.geocoding_field])
    },
    set_geo_values: function () {
        var self = this;

        var partner_id = false;
        if (this.field_manager.fields && this.field_manager.fields[this.name]) {
            partner_id = this.field_manager.get_field_value(this.name);
        }
        var type = self.field.type;
        if (!partner_id || type != "many2one" ) {
            self.set({"geo_lat": undefined});
            self.set({"geo_lng": undefined});
            self.set({"geocoding": undefined});
            self.dfd_geo_values.resolve();
        }else{
            var ResPartner = new Model("res.partner");
            ResPartner._context = ResPartner.context({'active_test': false})
            // retrieve geo values from db
            ResPartner.query(['id', 'geo_lat', 'geo_lng', 'precision', 'geocoding', 'name'])
                .filter([['id', '=', partner_id]]) // id
                .all()
                .then(function (partners){
                    var tooltip_title_noloc, tooltip_title_verif;
                    if (!!partners[0]["name"]) {
                        tooltip_title_noloc = partners[0]["name"] + " n'est pas géolocalisé.";
                        tooltip_title_verif = "La géolocalisation de " + partners[0]["name"] + " est à vérifier.";
                    }else{
                        tooltip_title_noloc = "cette adresse n'est pas géolocalisée.";
                        tooltip_title_verif = "La géolosalisation de cette adresse est à vérifier.";
                    }
                    if (self.get("id") != partner_id && !!self.get("geo_class_id")) {  // value changed
                        $("." + self.get("geo_class_id")).remove();
                        self.$geo_warning = undefined;
                        self.$geo_button = undefined;
                    }
                    self.set({
                        "geo_lat": partners[0]["geo_lat"],
                        "geo_lng": partners[0]["geo_lng"],
                        "precision": partners[0]["precision"],
                        "geocoding": partners[0]["geocoding"],
                        "tooltip_title_noloc": tooltip_title_noloc,
                        "tooltip_title_verif": tooltip_title_verif,
                        "id": partner_id,
                        "geo_class_id": "of_geo_partner_m2o_" + partner_id,
                    });
                    // on peut vérifier la géo_loc maintenant
                    self.dfd_geo_values.resolve();
                    return partners[0]["geo_lat"]
                })
        }

    },
    check_localized: function() {
        // on considère que s'il n'y a pas de partenaire c'est géolocalisé, par convention
        var partner_lat = this.get('geo_lat');
        var partner_lng = this.get('geo_lng');
        if (partner_lat === 0 && partner_lng === 0) {
            return false;
        }else if (this.get('geocoding') == 'need_verif') {
            return undefined;
        }
        return true;
    },
    render_value: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.render_geo_buttons();
    },
    render_geo_buttons: function() {
        var self = this;

        if (this.field.relation == 'res.partner') {
            this.dfd_geo_values = $.Deferred()
            this.set_geo_values();
            // on attend d'avoir set la valeur de geo_lat avant de la verifier :D

            $.when(this.dfd_geo_values).then(function(){
                var localized = self.check_localized();
                if(!localized && !self.get("invisible")) {
                    // n'est pas géolocalisé
                    var options = _.extend({
                        delay: { show: 501, hide: 0 },
                        title: _t("Cliquez ici pour tenter de géolocaliser ce partenaire avec votre géocodeur par défaut"),
                    });
                    if ((self.get("precision") == "not_tried" || self.get("geocoding") == "not_tried") && isNullOrUndef(self.$geo_button)) {
                        self.$geo_button = $('<span/>').addClass('fa fa-map-marker fa-lg of_ws_lr of_icon_button ' + self.get("geo_class_id"))
                        .appendTo(self.$icon_buttons).tooltip(options)
                        .click(self.geocode_fast.bind(self))//;}, 10);
                    }else if (self.get("precision") != "not_tried" && self.get("geocoding") != "not_tried" && !isNullOrUndef(self.$geo_button)) {
                        self.$geo_button.remove()
                        self.$geo_button = undefined;
                    }

                    if (isNullOrUndef(self.$geo_warning)) {
                        if (localized == undefined) {
                            // location needs verification, we show an orange warning
                            options["title"] = _t(self.get('tooltip_title_verif'));
                            self.$geo_warning = $('<span/>').addClass(
                                'fa fa-exclamation-triangle of_icon_button of_orange of_ws_l '
                                + self.get("geo_class_id"))
                            .insertAfter(self.$label).tooltip(options);
                        }else{
                            // not localized, we show a red warning
                            options["title"] = _t(self.get('tooltip_title_noloc'));
                            self.$geo_warning = $('<span/>').addClass(
                                'fa fa-exclamation-triangle of_icon_button of_red of_ws_l '
                                + self.get("geo_class_id"))
                            .insertAfter(self.$label).tooltip(options);
                        }
                    }
                }else if (localized) {
                    $("." + self.get("geo_class_id")).remove();
                    self.$geo_warning = undefined;
                    self.$geo_button = undefined;
                }
            });
        }
    },
    geocode_fast: function() {
        var self = this;
        var ResPartner = new Model("res.partner");
        ResPartner.call("geo_code", [[this.get("id")]])
        .then(function () {
            self.render_value();
        })
    },
});


});
