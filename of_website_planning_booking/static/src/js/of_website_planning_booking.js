odoo.define("of_website_planning_booking.of_booking", function (require) {
    "use strict";

    var ajax = require("web.ajax");
    var core = require("web.core");
    var publicWidget = require("web.public.widget");
    var wUtils = require("website.utils");
    var QWeb = core.qweb;
    var _t = core._t;

    publicWidget.registry.OFWebsiteBooking = publicWidget.Widget.extend({
        selector: ".of_booking_main",
        xmlDependencies: [
            "/of_website_planning_booking/static/src/xml/of_booking_slot_kanban.xml",
        ],

        _isValid: function (value) {
            return (
                value != null &&
                value != undefined &&
                value != "" &&
                !Number.isNaN(value)
            );
        },

        init: function () {
            this._super.apply(this, arguments);

            this.service_card = false;
            this.contract_card = false;
            this.address_card = false;
            this.address_select = false;
            this.slot_card = false;
            this.slots_div = false;
            this.no_slot_div = false;
            this.booking_slots_div = false;
            this.slot_error = false;
            this.popup_text = false;
            this.service_selector = false;
            this.contract_selector = false;
            this.address_selector = false;
            this.name_input = false;
            this.email_input = false;
            this.phone_input = false;
            this.street_input = false;
            this.street2_input = false;
            this.zip_input = false;
            this.city_input = false;
            this.from_date_input = false;
            this.logged_partner_id = false;
            this.session_mode = false;
            this.session_service_id = false;
            this.session_contract_id = false;
            this.session_partner_id = false;
            this.session_from_date = false;
            this.params = false;
        },

        start() {
            const def = this._super(...arguments);

            var self = this;

            self.service_card = self.$("div#service_card");
            self.contract_card = self.$("div#contract_card");
            self.address_card = self.$("div#address_card");
            self.address_select = self.$("div#address_select");
            self.slot_card = self.$("div#slot_card");
            self.slots_div = self.$("div#slots_div");
            self.no_slot_div = self.$("div#no_slot_div");
            self.booking_slots_div = self.$("div#of_booking_slots");
            self.slot_error = self.$("div#slot_error");

            self.popup_text = $("span#popup-text");

            self.service_selector = self.$("select#service_id");

            self.contract_selector = self.$("select#contract_id");

            self.address_selector = self.$("select#address_id");
            self.name_input = self.$("input#name");
            self.email_input = self.$("input#email");
            self.phone_input = self.$("input#phone");
            self.street_input = self.$("input#street");
            self.street2_input = self.$("input#street2");
            self.zip_input = self.$("input#zip");
            self.city_input = self.$("input#city");

            self.from_date_input = self.$("input#from_date");

            self.logged_partner_id = self.$("input#logged_partner_id").val();

            self.params = new URLSearchParams(window.location.search);

            self.$(".collapse").on("show.bs.collapse", function () {
                $(this).siblings(".card-header").addClass("active");
            });

            self.$(".collapse").on("hide.bs.collapse", function () {
                $(this).siblings(".card-header").removeClass("active");
            });

            if (self.params.get("of_return") == "1") {
                self.session_mode = sessionStorage.getItem("of_booking_mode");
                self.session_service_id = sessionStorage.getItem(
                    "of_booking_service_id"
                );
                self.session_contract_id = sessionStorage.getItem(
                    "of_booking_contract_id"
                );
                self.session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );
                self.session_from_date = sessionStorage.getItem("of_booking_from_date");

                var newUrl = new URL(window.location.href);
                newUrl.searchParams.delete("of_return");
                history.replaceState({}, null, newUrl.href);
            } else {
                // On ne retire pas du cache of_booking_partner_id pour éviter la création de doublons de partenaire
                sessionStorage.removeItem("of_booking_mode");
                sessionStorage.removeItem("of_booking_service_id");
                sessionStorage.removeItem("of_booking_contract_id");

                self.session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );
                self.session_from_date = sessionStorage.getItem("of_booking_from_date");
            }

            if (
                self.session_mode == null ||
                self.session_mode == undefined ||
                self.session_mode == ""
            ) {
                if (self.logged_partner_id != 0) {
                    if (self.$("select#contract_id option").length > 1) {
                        self.session_mode = "contract";
                        self.address_select.hide();
                    } else {
                        self.session_mode = "service";
                    }
                } else {
                    self.session_mode = "service";
                    self.address_select.hide();
                }
                sessionStorage.setItem("of_booking_mode", self.session_mode);
            }

            if (self.session_mode == "service") {
                self.contract_card.hide();
                self.service_card.show();

                if (self._isValid(self.session_service_id)) {
                    self.service_selector.val(self.session_service_id);
                    self.service_card.find(".collapse").collapse("hide");
                    self.address_card.show();
                    if (!self._isValid(self.session_partner_id)) {
                        self.address_card.find(".collapse").collapse("show");
                    }
                } else {
                    self.service_card.find(".collapse").collapse("show");
                    self.service_selector.val("");
                }

                if (self.$("select#address_id option").length > 1) {
                    self.address_select.show();
                } else {
                    self.address_select.hide();
                }
            } else if (self.session_mode == "contract") {
                self.contract_card.show();
                self.service_card.hide();

                if (self._isValid(self.session_contract_id)) {
                    self.contract_selector.val(self.session_contract_id);
                    self.contract_card.find(".collapse").collapse("hide");
                    self.address_card.show();
                    if (!self._isValid(self.session_partner_id)) {
                        self.address_card.find(".collapse").collapse("show");
                    }
                } else {
                    self.contract_card.find(".collapse").collapse("show");
                    self.contract_selector.val("");
                }

                self.address_select.hide();
            }

            if (
                self.session_from_date != null &&
                self.session_from_date != undefined &&
                self.session_from_date != ""
            ) {
                self.from_date_input.val(self.session_from_date);
            } else {
                var tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                var tomorrow_str = moment(tomorrow).format("YYYY-MM-DD");
                self.from_date_input.val(tomorrow_str);
            }

            if (
                (self._isValid(self.session_service_id) ||
                    self._isValid(self.session_contract_id)) &&
                self._isValid(self.session_partner_id)
            ) {
                ajax.jsonRpc("/booking/get_partner", "call", {
                    partner_id: self.session_partner_id,
                })
                    .then(function (result) {
                        var partner = JSON.parse(result);
                        self.name_input.val(partner.name);
                        self.email_input.val(partner.email);
                        self.phone_input.val(partner.phone);
                        self.street_input.val(partner.street);
                        self.street2_input.val(partner.street2 || "");
                        self.zip_input.val(partner.zip);
                        self.city_input.val(partner.city);

                        self.address_selector.val(self.session_partner_id);

                        self.address_card.find(".collapse").collapse("hide");

                        self.slot_card.show();
                        self.slot_card.find(".collapse").collapse("show");

                        self.from_date_input.change();
                    })
                    .catch((error) => {
                        window.location.href = "/booking/error";
                    });
            }

            self.$("#my_contracts").on("click", function (event) {
                self.session_mode = "contract";
                sessionStorage.setItem("of_booking_mode", self.session_mode);
                sessionStorage.removeItem("of_booking_service_id");
                self.service_selector.val("");
                self.service_card.hide();
                self.service_card.find(".collapse").collapse("hide");
                self.contract_card.show();
                self.contract_card.find(".collapse").collapse("show");
                self.address_select.hide();
                self.address_card.hide();
                self.address_card.find(".collapse").collapse("hide");
                self.slot_card.hide();
                self.slot_card.find(".collapse").collapse("hide");
            });

            self.$("#other_services").on("click", function (event) {
                self.session_mode = "service";
                sessionStorage.setItem("of_booking_mode", self.session_mode);
                sessionStorage.removeItem("of_booking_contract_id");
                self.contract_selector.val("");
                self.service_card.show();
                self.service_card.find(".collapse").collapse("show");
                self.contract_card.hide();
                self.contract_card.find(".collapse").collapse("hide");
                if (self.$("select#address_id option").length > 1) {
                    self.address_select.show();
                } else {
                    self.address_select.hide();
                }
                self.address_card.hide();
                self.address_card.find(".collapse").collapse("hide");
                self.slot_card.hide();
                self.slot_card.find(".collapse").collapse("hide");
            });

            self.service_selector.on("change", function (event) {
                var service_id = self.service_selector.find(":selected").val();
                if (self._isValid(service_id)) {
                    sessionStorage.setItem("of_booking_service_id", service_id);
                    self.session_service_id = service_id;

                    self.service_selector.removeClass("is-invalid");
                    self.service_card.find(".collapse").collapse("hide");

                    self.address_card.show();
                    self.address_card.find(".collapse").collapse("show");

                    if (!self._isValid(self.session_partner_id) && self.logged_partner_id != 0) {
                        ajax.jsonRpc("/booking/get_partner", "call", {
                            partner_id: self.logged_partner_id,
                        })
                            .then(function (result) {
                                var partner = JSON.parse(result);
                                self.name_input.val(partner.name);
                                self.email_input.val(partner.email);
                                self.phone_input.val(partner.phone);
                                self.street_input.val(partner.street);
                                self.street2_input.val(partner.street2 || "");
                                self.zip_input.val(partner.zip);
                                self.city_input.val(partner.city);

                                self.address_selector.val(self.logged_partner_id);

                                sessionStorage.setItem(
                                    "of_booking_partner_id",
                                    self.logged_partner_id
                                );
                            })
                            .catch((error) => {
                                window.location.href = "/booking/error";
                            });
                    } else if (
                        self._isValid(self.session_partner_id)
                    ) {
                        ajax.jsonRpc("/booking/get_partner", "call", {
                            partner_id: self.session_partner_id,
                        })
                            .then(function (result) {
                                var partner = JSON.parse(result);
                                self.name_input.val(partner.name);
                                self.email_input.val(partner.email);
                                self.phone_input.val(partner.phone);
                                self.street_input.val(partner.street);
                                self.street2_input.val(partner.street2 || "");
                                self.zip_input.val(partner.zip);
                                self.city_input.val(partner.city);

                                self.address_selector.val(self.session_partner_id);

                                sessionStorage.setItem(
                                    "of_booking_partner_id",
                                    self.session_partner_id
                                );
                            })
                            .catch((error) => {
                                window.location.href = "/booking/error";
                            });
                    }

                    self.slots_div.hide();
                    self.no_slot_div.hide();
                } else {
                    self.service_selector.addClass("is-invalid");
                }
            });

            self.contract_selector.on("change", function (event) {
                var contract_id = self.contract_selector.find(":selected").val();
                if (self._isValid(contract_id)) {
                    sessionStorage.setItem("of_booking_contract_id", contract_id);
                    self.session_contract_id = contract_id;

                    self.contract_selector.removeClass("is-invalid");
                    self.contract_card.find(".collapse").collapse("hide");

                    self.address_card.show();
                    self.address_card.find(".collapse").collapse("show");

                    ajax.jsonRpc("/booking/get_partner", "call", {
                        partner_id: self.logged_partner_id,
                        contract_id: self.session_contract_id,
                    })
                        .then(function (result) {
                            var partner = JSON.parse(result);
                            self.name_input.val(partner.name);
                            self.email_input.val(partner.email);
                            self.phone_input.val(partner.phone);
                            self.street_input.val(partner.street);
                            self.street2_input.val(partner.street2 || "");
                            self.zip_input.val(partner.zip);
                            self.city_input.val(partner.city);

                            sessionStorage.setItem("of_booking_partner_id", partner.id);
                        })
                        .catch((error) => {
                            window.location.href = "/booking/error";
                        });

                    self.slots_div.hide();
                    self.no_slot_div.hide();
                } else {
                    self.contract_selector.addClass("is-invalid");
                }
            });

            self.address_selector.on("change", function (event) {
                var address_id = self.address_selector.find(":selected").val();
                if (self._isValid(address_id)) {
                    ajax.jsonRpc("/booking/get_partner", "call", {
                        partner_id: address_id,
                    })
                        .then(function (result) {
                            var partner = JSON.parse(result);
                            self.name_input.val(partner.name);
                            self.email_input.val(partner.email);
                            self.phone_input.val(partner.phone);
                            self.street_input.val(partner.street);
                            self.street2_input.val(partner.street2 || "");
                            self.zip_input.val(partner.zip);
                            self.city_input.val(partner.city);

                            sessionStorage.setItem("of_booking_partner_id", address_id);
                        })
                        .catch((error) => {
                            window.location.href = "/booking/error";
                        });
                }
            });

            self.$("#new_address").on("click", function (event) {
                self.address_selector.val("");
                self.name_input.val("");
                self.email_input.val("");
                self.phone_input.val("");
                self.street_input.val("");
                self.street2_input.val("");
                self.zip_input.val("");
                self.city_input.val("");
                sessionStorage.removeItem("of_booking_partner_id");
            });

            self.$("#address_submit").on("click", function (event) {
                var session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );

                var name = self.name_input.val();
                var name_ok = false;
                var email = self.email_input.val();
                var email_ok = false;
                var phone = self.phone_input.val();
                var phone_ok = false;
                var street = self.street_input.val();
                var street_ok = false;
                var street2 = self.street2_input.val();
                var zip = self.zip_input.val();
                var zip_ok = false;
                var city = self.city_input.val();
                var city_ok = false;

                if (name != null && name != undefined && name != "") {
                    name_ok = true;
                    self.name_input.removeClass("is-invalid");
                } else {
                    self.name_input.addClass("is-invalid");
                }

                if (
                    email != null &&
                    email != undefined &&
                    email != "" &&
                    email.match(
                        /^([\w-\.]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([\w-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?)$/
                    )
                ) {
                    email_ok = true;
                    self.email_input.removeClass("is-invalid");
                } else {
                    self.email_input.addClass("is-invalid");
                }

                if (phone != null && phone != undefined && phone != "") {
                    phone_ok = true;
                    self.phone_input.removeClass("is-invalid");
                } else {
                    self.phone_input.addClass("is-invalid");
                }

                if (street != null && street != undefined && street != "") {
                    street_ok = true;
                    self.street_input.removeClass("is-invalid");
                } else {
                    self.street_input.addClass("is-invalid");
                }

                if (zip != null && zip != undefined && zip != "") {
                    zip_ok = true;
                    self.zip_input.removeClass("is-invalid");
                } else {
                    self.zip_input.addClass("is-invalid");
                }

                if (city != null && city != undefined && city != "") {
                    city_ok = true;
                    self.city_input.removeClass("is-invalid");
                } else {
                    self.city_input.addClass("is-invalid");
                }

                if (name_ok && email_ok && phone_ok && street_ok && zip_ok && city_ok) {
                    // Show spinner popup
                    $(".container").addClass("show-popup");
                    self.popup_text.html(
                        _t("One moment please, we are looking for the best slot for your request.")
                    );

                    ajax.jsonRpc("/booking/create_update_partner", "call", {
                        partner_id: session_partner_id,
                        name: name,
                        email: email,
                        phone: phone,
                        street: street,
                        street2: street2,
                        zip: zip,
                        city: city,
                    })
                        .then(function (partner_id) {
                            sessionStorage.setItem("of_booking_partner_id", partner_id);
                            if (
                                self.$(
                                    "select#address_id option[value='" +
                                        partner_id +
                                        "']"
                                ).length == 0
                            ) {
                                self.address_selector.append(
                                    $("<option>", {
                                        value: partner_id,
                                        text: zip + " - " + city,
                                    })
                                );
                                self.address_selector.val(partner_id);
                            }
                            self.address_card.find(".collapse").collapse("hide");
                            self.slot_card.show();
                            self.slot_card.find(".collapse").collapse("show");
                            self.slot_card[0].scrollIntoView();

                            self.from_date_input.change();
                        })
                        .catch((error) => {
                            window.location.href = "/booking/error";
                        });
                }
            });

            self.from_date_input.on("change", function (event) {
                if (!$(".container").hasClass("show-popup")) {
                    // Show spinner popup
                    $(".container").addClass("show-popup");
                    self.popup_text.html(
                        _t("One moment please, we are looking for the best slot for your request.")
                    );
                }

                var from_date = self.from_date_input.val();
                sessionStorage.setItem("of_booking_from_date", from_date);
                self.session_from_date = from_date;

                self.session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );

                ajax.jsonRpc("/booking/search_slots", "call", {
                    service_id: self.session_service_id,
                    contract_id: self.session_contract_id,
                    partner_id: self.session_partner_id,
                    from_date: self.session_from_date,
                })
                    .then(function (result) {
                        self.booking_slots_div.html("");
                        $("#search_more_submit").show();
                        $("#slot_submit").show();

                        var slots = result[0];
                        var search_more = result[1];
                        var last_day = "";
                        var last_desc = "";

                        for (var i = 0; i < slots.length; i++) {
                            var slot = slots[i];
                            var $slot_div = $(
                                QWeb.render("of_website_planning_booking.slot_kanban", {
                                    title: slot.name,
                                    extra_info: slot.description,
                                    slot_id: slot.id,
                                })
                            );
                            if (slot.description == "Matin") {
                                if (last_desc == "Matin") {
                                    var $unavailable_slot_div = $(
                                        QWeb.render(
                                            "of_website_planning_booking.unavailable_slot_kanban"
                                        )
                                    );
                                    $unavailable_slot_div.addClass("float-end");
                                    self.booking_slots_div.append(
                                        $unavailable_slot_div
                                    );
                                }
                                self.booking_slots_div.append(
                                    '<div class="clearfix"/>'
                                );
                                $slot_div.addClass("float-start");
                            } else {
                                if (slot.name !== last_day) {
                                    if (last_desc == "Matin") {
                                        var $unavailable_slot_div = $(
                                            QWeb.render(
                                                "of_website_planning_booking.unavailable_slot_kanban"
                                            )
                                        );
                                        $unavailable_slot_div.addClass("float-end");
                                        self.booking_slots_div.append(
                                            $unavailable_slot_div
                                        );
                                    }
                                    self.booking_slots_div.append(
                                        '<div class="clearfix"/>'
                                    );
                                    var $unavailable_slot_div = $(
                                        QWeb.render(
                                            "of_website_planning_booking.unavailable_slot_kanban"
                                        )
                                    );
                                    $unavailable_slot_div.addClass("float-start");
                                    self.booking_slots_div.append(
                                        $unavailable_slot_div
                                    );
                                }
                                $slot_div.addClass("float-end");
                            }
                            $slot_div.on("click", self._onClickSlot);
                            self.booking_slots_div.append($slot_div);
                            if (slot.description === "Après-midi") {
                                self.booking_slots_div.append(
                                    '<div class="clearfix"/>'
                                );
                            }
                            last_day = slot.name;
                            last_desc = slot.description;
                        }

                        if (last_desc == "Matin") {
                            var $unavailable_slot_div = $(
                                QWeb.render(
                                    "of_website_planning_booking.unavailable_slot_kanban"
                                )
                            );
                            $unavailable_slot_div.addClass("float-end");
                            self.booking_slots_div.append($unavailable_slot_div);
                        }

                        if (search_more == 0) {
                            $("#search_more_submit").hide();
                        }

                        if (slots.length == 0) {
                            self.slots_div.hide();
                            self.no_slot_div.show();
                        } else {
                            self.slots_div.show();
                            self.no_slot_div.hide();
                        }

                        // Hide spinner popup
                        $(".container").removeClass("show-popup");
                    })
                    .catch((error) => {
                        window.location.href = "/booking/error";
                    });
            });

            $("#search_more_submit").on("click", function (event) {
                // Show spinner popup
                $(".container").addClass("show-popup");
                self.popup_text.html(
                    _t("One moment please, we are looking for additional slots.")
                );

                ajax.jsonRpc("/booking/search_slots", "call", {
                    service_id: self.session_service_id,
                    contract_id: self.session_contract_id,
                    partner_id: self.session_partner_id,
                    from_date: self.session_from_date,
                    search_more: 1,
                })
                    .then(function (result) {
                        self.booking_slots_div.html("");

                        var slots = result[0];
                        var search_more = result[1];
                        var last_day = "";
                        var last_desc = "";

                        for (var i = 0; i < slots.length; i++) {
                            var slot = slots[i];
                            var $slot_div = $(
                                QWeb.render("of_website_planning_booking.slot_kanban", {
                                    title: slot.name,
                                    extra_info: slot.description,
                                    slot_id: slot.id,
                                })
                            );
                            if (slot.description == "Matin") {
                                if (last_desc == "Matin") {
                                    var $unavailable_slot_div = $(
                                        QWeb.render(
                                            "of_website_planning_booking.unavailable_slot_kanban"
                                        )
                                    );
                                    $unavailable_slot_div.addClass("float-end");
                                    self.booking_slots_div.append(
                                        $unavailable_slot_div
                                    );
                                }
                                self.booking_slots_div.append(
                                    '<div class="clearfix"/>'
                                );
                                $slot_div.addClass("float-start");
                            } else {
                                if (slot.name !== last_day) {
                                    if (last_desc == "Matin") {
                                        var $unavailable_slot_div = $(
                                            QWeb.render(
                                                "of_website_planning_booking.unavailable_slot_kanban"
                                            )
                                        );
                                        $unavailable_slot_div.addClass("float-end");
                                        self.booking_slots_div.append(
                                            $unavailable_slot_div
                                        );
                                    }
                                    self.booking_slots_div.append(
                                        '<div class="clearfix"/>'
                                    );
                                    var $unavailable_slot_div = $(
                                        QWeb.render(
                                            "of_website_planning_booking.unavailable_slot_kanban"
                                        )
                                    );
                                    $unavailable_slot_div.addClass("float-start");
                                    self.booking_slots_div.append(
                                        $unavailable_slot_div
                                    );
                                }
                                $slot_div.addClass("float-end");
                            }
                            $slot_div.on("click", self._onClickSlot);
                            self.booking_slots_div.append($slot_div);
                            if (slot.description === "Après-midi") {
                                self.booking_slots_div.append(
                                    '<div class="clearfix"/>'
                                );
                            }
                            last_day = slot.name;
                            last_desc = slot.description;
                        }

                        if (last_desc == "Matin") {
                            var $unavailable_slot_div = $(
                                QWeb.render(
                                    "of_website_planning_booking.unavailable_slot_kanban"
                                )
                            );
                            $unavailable_slot_div.addClass("float-end");
                            self.booking_slots_div.append($unavailable_slot_div);
                        }

                        if (search_more == 0) {
                            $("#search_more_submit").hide();
                        }

                        // Hide spinner popup
                        $(".container").removeClass("show-popup");
                    })
                    .catch((error) => {
                        window.location.href = "/booking/error";
                    });
            });

            $("#slot_submit").on("click", function (event) {
                var selected_slot = self.booking_slots_div.find(
                    ".card.of-border-primary"
                );
                var selected_slot_id = selected_slot.find("input#slot_id").val();

                if (self._isValid(selected_slot_id)) {
                    self.slot_error.hide();

                    return wUtils.sendRequest("/booking/confirm", {
                        csrf_token: core.csrf_token,
                        service_id: self.session_service_id,
                        contract_id: self.session_contract_id,
                        partner_id: self.session_partner_id,
                        slot_id: selected_slot_id,
                    });
                } else {
                    self.slot_error.show();
                }
            });

            return def;
        },

        _onClickSlot: function (event) {
            $(self.slot_error).hide();

            var old_slot = $(self.of_booking_slots).find(".card.of-border-primary");
            old_slot.addClass("of_js_slot_change");
            old_slot.removeClass("of-border-primary");

            var new_slot = $(this).find(".card");
            new_slot.find(".btn-ship").toggle();
            new_slot.removeClass("of_js_slot_change");
            new_slot.addClass("of-border-primary");
        },
    });
});
