/* eslint complexity:0 */

odoo.define("of_website_planning_booking.of_booking", function (require) {
    "use strict";

    const ajax = require("web.ajax");
    const core = require("web.core");
    const publicWidget = require("web.public.widget");
    const wUtils = require("website.utils");
    const QWeb = core.qweb;
    const { _t } = core;

    publicWidget.registry.OFWebsiteBooking = publicWidget.Widget.extend({
        selector: ".of_booking_main",
        xmlDependencies: [
            "/of_website_planning_booking/static/src/xml/of_booking_slot_kanban.xml",
        ],

        _isValid: function (value) {
            return (
                value !== null &&
                value !== undefined &&
                value !== "" &&
                value !== false &&
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

            const self = this;

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

            self.logged_partner_id = self.$("input#logged_partner_id").val() || 0;

            self.params = new URLSearchParams(window.location.search);

            self.$(".collapse").on("show.bs.collapse", function () {
                $(this).siblings(".card-header").addClass("active");
            });

            self.$(".collapse").on("hide.bs.collapse", function () {
                $(this).siblings(".card-header").removeClass("active");
            });

            if (self.params.get("of_return") === "1") {
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

                const newUrl = new URL(window.location.href);
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
                self.session_mode === null ||
                self.session_mode === undefined ||
                self.session_mode === false
            ) {
                if (self.logged_partner_id === 0) {
                    self.session_mode = "service";
                    self.address_select.hide();
                } else if (self.$("select#contract_id option").length > 1) {
                    self.session_mode = "contract";
                    self.address_select.hide();
                } else {
                    self.session_mode = "service";
                }
                sessionStorage.setItem("of_booking_mode", self.session_mode);
            }

            if (self.session_mode === "service") {
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
            } else if (self.session_mode === "contract") {
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
                self.session_from_date !== null &&
                self.session_from_date !== undefined &&
                self.session_from_date !== ""
            ) {
                self.from_date_input.val(self.session_from_date);
            } else {
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                const tomorrow_str = moment(tomorrow).format("YYYY-MM-DD");
                self.from_date_input.val(tomorrow_str);
            }

            if (
                self._isValid(self.session_partner_id) &&
                self._isValid(self.session_service_id || self.session_contract_id)
            ) {
                /**
                 * We don't want to display the time slot map when `session_contract_id` or `session_service_id` are
                 * `false` according to their respective session mode.
                 */
                const showSlotCard =
                    !(self.session_mode === "contract" && !self.session_contract_id) &&
                    !(self.session_mode === "service" && !self.session_service_id);

                self._fetchPartnerAndUpdateUI(self.session_partner_id, {
                    partner_id: self.session_partner_id,
                    hideAddressCard: true,
                    showSlotCard: showSlotCard,
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
                const service_id = self.service_selector.find(":selected").val() || 0;
                if (self._isValid(service_id)) {
                    sessionStorage.setItem("of_booking_service_id", service_id);
                    self.session_service_id = service_id;

                    sessionStorage.removeItem("of_booking_contract_id");

                    self.service_selector.removeClass("is-invalid");
                    self.service_card.find(".collapse").collapse("hide");

                    self.address_card.show();
                    self.address_card.find(".collapse").collapse("show");

                    if (
                        !self._isValid(self.session_partner_id) &&
                        self.logged_partner_id !== 0
                    ) {
                        self._fetchPartnerAndUpdateUI(self.logged_partner_id, {
                            partner_id: self.logged_partner_id,
                        });
                    } else if (self._isValid(self.session_partner_id)) {
                        self._fetchPartnerAndUpdateUI(self.session_partner_id, {
                            partner_id: self.session_partner_id,
                        });
                    }
                    self.slots_div.hide();
                    self.no_slot_div.hide();
                } else {
                    self.service_selector.addClass("is-invalid");
                }
            });

            self.contract_selector.on("change", function (event) {
                const contract_id = self.contract_selector.find(":selected").val();
                if (self._isValid(contract_id)) {
                    sessionStorage.setItem("of_booking_contract_id", contract_id);
                    self.session_contract_id = contract_id;

                    sessionStorage.removeItem("of_booking_service_id");

                    self.contract_selector.removeClass("is-invalid");
                    self.contract_card.find(".collapse").collapse("hide");

                    self.address_card.show();
                    self.address_card.find(".collapse").collapse("show");

                    self._fetchPartnerAndUpdateUI(self.logged_partner_id, {
                        partner_id: self.logged_partner_id,
                        contract_id: self.session_contract_id,
                    });

                    self.slots_div.hide();
                    self.no_slot_div.hide();
                } else {
                    self.contract_selector.addClass("is-invalid");
                }
            });

            self.address_selector.on("change", function (event) {
                const address_id = self.address_selector.find(":selected").val() || 0;
                if (self._isValid(address_id)) {
                    self._fetchPartnerAndUpdateUI(address_id, {
                        partner_id: address_id,
                    });
                }
            });

            self.$("#new_address").on("click", function (event) {
                self._fetchPartnerAndUpdateUI(self.logged_partner_id, {
                    resetAddress: true,
                });
            });

            self.$("#address_submit").on("click", function (event) {
                const session_partner_id = sessionStorage.getItem(
                    "of_booking_partner_id"
                );

                const name = self.name_input.val();
                let name_ok = false;
                const email = self.email_input.val();
                let email_ok = false;
                const phone = self.phone_input.val();
                let phone_ok = false;
                const street = self.street_input.val();
                let street_ok = false;
                const street2 = self.street2_input.val();
                const zip = self.zip_input.val();
                let zip_ok = false;
                const city = self.city_input.val();
                let city_ok = false;

                if (name !== null && name !== undefined && name !== "") {
                    name_ok = true;
                    self.name_input.removeClass("is-invalid");
                } else {
                    self.name_input.addClass("is-invalid");
                }

                if (
                    email !== null &&
                    email !== undefined &&
                    email !== "" &&
                    email.match(
                        /^([\w-\.]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([\w-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?)$/
                    )
                ) {
                    email_ok = true;
                    self.email_input.removeClass("is-invalid");
                } else {
                    self.email_input.addClass("is-invalid");
                }

                if (phone !== null && phone !== undefined && phone !== "") {
                    phone_ok = true;
                    self.phone_input.removeClass("is-invalid");
                } else {
                    self.phone_input.addClass("is-invalid");
                }

                if (street !== null && street !== undefined && street !== "") {
                    street_ok = true;
                    self.street_input.removeClass("is-invalid");
                } else {
                    self.street_input.addClass("is-invalid");
                }

                if (zip !== null && zip !== undefined && zip !== "") {
                    zip_ok = true;
                    self.zip_input.removeClass("is-invalid");
                } else {
                    self.zip_input.addClass("is-invalid");
                }

                if (city !== null && city !== undefined && city !== "") {
                    city_ok = true;
                    self.city_input.removeClass("is-invalid");
                } else {
                    self.city_input.addClass("is-invalid");
                }

                if (name_ok && email_ok && phone_ok && street_ok && zip_ok && city_ok) {
                    // Show spinner popup
                    $(".container").addClass("show-popup");
                    self.popup_text.html(
                        _t(
                            "One moment please, we are looking for the best slot for your request."
                        )
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
                                    `select#address_id option[value="${partner_id}"]`
                                ).length === 0
                            ) {
                                self.address_selector.append(
                                    $("<option>", {
                                        value: partner_id,
                                        text: `${zip} - ${city}`,
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
                        _t(
                            "One moment please, we are looking for the best slot for your request."
                        )
                    );
                }

                const from_date = self.from_date_input.val();
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

                        const slots = result[0];
                        const searchMore = result[1];
                        let lastDay = "";
                        let lastDesc = "";

                        for (let i = 0; i < slots.length; i++) {
                            const slot = slots[i];
                            const $slotDiv = $(
                                QWeb.render("of_website_planning_booking.slot_kanban", {
                                    title: slot.name,
                                    extra_info: slot.description,
                                    slot_id: slot.id,
                                })
                            );
                            if (slot.description === _t("Morning")) {
                                if (lastDesc === _t("Morning")) {
                                    self.booking_slots_div.append(
                                        self._createUnavailableSlotDiv("float-end")
                                    );
                                }
                                self._appendClearfix(self.booking_slots_div);
                                $slotDiv.addClass("float-start");
                            } else {
                                if (slot.name !== lastDay) {
                                    if (lastDesc === _t("Morning")) {
                                        self.booking_slots_div.append(
                                            self._createUnavailableSlotDiv("float-end")
                                        );
                                    }
                                    self._appendClearfix(self.booking_slots_div);
                                    self.booking_slots_div.append(
                                        self._createUnavailableSlotDiv("float-start")
                                    );
                                }
                                $slotDiv.addClass("float-end");
                            }
                            $slotDiv.on("click", self._onClickSlot);
                            self.booking_slots_div.append($slotDiv);
                            if (slot.description === _t("Afternoon")) {
                                self._appendClearfix(self.booking_slots_div);
                            }
                            lastDay = slot.name;
                            lastDesc = slot.description;
                        }

                        if (lastDesc === _t("Morning")) {
                            self.booking_slots_div.append(
                                self._createUnavailableSlotDiv("float-end")
                            );
                        }

                        if (searchMore === false) {
                            $("#search_more_submit").hide();
                        }

                        if (slots.length === 0) {
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
                    search_more: true,
                })
                    .then(function (result) {
                        self.booking_slots_div.html("");

                        const slots = result[0];
                        const searchMore = result[1];
                        let lastDay = "";
                        let lastDesc = "";

                        for (let i = 0; i < slots.length; i++) {
                            const slot = slots[i];
                            const $slotDiv = $(
                                QWeb.render("of_website_planning_booking.slot_kanban", {
                                    title: slot.name,
                                    extra_info: slot.description,
                                    slot_id: slot.id,
                                })
                            );
                            if (slot.description === _t("Morning")) {
                                if (lastDesc === _t("Morning")) {
                                    self.booking_slots_div.append(
                                        self._createUnavailableSlotDiv("float-end")
                                    );
                                }
                                self._appendClearfix(self.booking_slots_div);
                                $slotDiv.addClass("float-start");
                            } else {
                                if (slot.name !== lastDay) {
                                    if (lastDesc === _t("Morning")) {
                                        self.booking_slots_div.append(
                                            self._createUnavailableSlotDiv("float-end")
                                        );
                                    }
                                    self._appendClearfix(self.booking_slots_div);
                                    self.booking_slots_div.append(
                                        self._createUnavailableSlotDiv("float-start")
                                    );
                                }
                                $slotDiv.addClass("float-end");
                            }
                            $slotDiv.on("click", self._onClickSlot);
                            self.booking_slots_div.append($slotDiv);
                            if (slot.description === _t("Afternoon")) {
                                self._appendClearfix(self.booking_slots_div);
                            }
                            lastDay = slot.name;
                            lastDesc = slot.description;
                        }

                        if (lastDesc === _t("Morning")) {
                            self.booking_slots_div.append(
                                self._createUnavailableSlotDiv("float-end")
                            );
                        }

                        if (searchMore === false) {
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
                const selectedSlot = self.booking_slots_div.find(
                    ".card.of-border-primary"
                );
                const selectedSlotId = selectedSlot.find("input#slot_id").val() || 0;

                if (self._isValid(selectedSlotId)) {
                    self.slot_error.hide();

                    return wUtils.sendRequest("/booking/confirm", {
                        csrf_token: core.csrf_token,
                        service_id: self.session_service_id,
                        contract_id: self.session_contract_id,
                        partner_id: self.session_partner_id,
                        slot_id: selectedSlotId,
                    });
                }
                self.slot_error.show();
            });

            return def;
        },

        /**
         * Updates fields address of the UI.
         * Thats also and store values in session storage and make some cards hidden/displayed depending on options.
         *
         * @param {Object} partner
         * @param {Object} options
         */
        _updatePartnerUI: function (partner, options = {}) {
            this.name_input.val(partner.name);
            this.email_input.val(partner.email);
            this.phone_input.val(partner.phone);
            this.street_input.val(partner.street);
            this.street2_input.val(partner.street2);
            this.zip_input.val(partner.zip);
            this.city_input.val(partner.city);

            let sessionBookingPartner = false;
            if (options.contract_id) {
                sessionBookingPartner = partner.id;
            } else {
                sessionBookingPartner = options.partner_id || false;
            }

            if (options.partner_id && !options.contract_id) {
                this.address_selector.val(options.partner_id);
            }
            if (sessionBookingPartner) {
                sessionStorage.setItem("of_booking_partner_id", sessionBookingPartner);
            }

            if (options.hideAddressCard) {
                this.address_card.find(".collapse").collapse("hide");
            }

            if (options.showSlotCard) {
                this.slot_card.show();
                this.slot_card.find(".collapse").collapse("show");
                this.from_date_input.change();
            }
        },

        /**
         * Get Partner data from Odoo and updates UI depending on values fetched and options.
         *
         * @param {Interger} partner_id
         * @param {Objet} options
         */
        _fetchPartnerAndUpdateUI: function (partner_id, options = {}) {
            const self = this;
            const params = { partner_id };
            if (options.contract_id) {
                params.contract_id = options.contract_id;
            }

            ajax.jsonRpc("/booking/get_partner", "call", params)
                .then(function (result) {
                    const partner = JSON.parse(result);

                    self._updatePartnerUI(partner, options);

                    if (options.resetAddress) {
                        self.street_input.val("");
                        self.street2_input.val("");
                        self.zip_input.val("");
                        self.city_input.val("");
                        sessionStorage.removeItem("of_booking_partner_id");
                    }
                })
                .catch(() => {
                    window.location.href = "/booking/error";
                });
        },

        /**
         * Appends a clearfix `div` to the given container.
         * @param {Element} container
         */
        _appendClearfix: function (container) {
            container.append('<div class="clearfix"/>');
        },

        /**
         * Render unavailable slot div.
         * @param {String} floatClass
         * @returns {Element} div
         */
        _createUnavailableSlotDiv: function (floatClass) {
            const $unavailableSlotDiv = $(
                QWeb.render("of_website_planning_booking.unavailable_slot_kanban")
            );
            $unavailableSlotDiv.addClass(floatClass);
            return $unavailableSlotDiv;
        },

        /**
         * Decorate the clicked div and remove decoration from the previous one.
         * @param {Event} event
         */
        _onClickSlot: function (event) {
            $(self.slot_error).hide(); // eslint-disable-line

            const oldSlotDiv = $(self.of_booking_slots).find(".card.of-border-primary"); // eslint-disable-line
            oldSlotDiv.addClass("of_js_slot_change");
            oldSlotDiv.removeClass("of-border-primary");

            const newSlotDiv = $(this).find(".card");
            newSlotDiv.find(".btn-ship").toggle();
            newSlotDiv.removeClass("of_js_slot_change");
            newSlotDiv.addClass("of-border-primary");
        },
    });
});
