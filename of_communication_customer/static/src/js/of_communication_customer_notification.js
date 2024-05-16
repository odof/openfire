/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

import { Markup } from 'web.utils';

registerPatch({
    name: "MessagingNotificationHandler",
    recordMethods: {
        /**
         * @override
         */
        async _handleNotification(message) {
            if (message.type === "of_banner_notification") {
                return this._handleNotificationBannerNotificationOF(message.payload);
            }
            if (message.type === "of_simple_notification") {
                return this._handleNotificationSimpleNotificationOF(message.payload);
            }
            return this._super(message);
        },

        async _handleNotificationSimpleNotificationOF({ message, message_is_html, sticky, title, type }) {
            let notificationType = type
            notificationType = ["warning", "danger", "success", "info"].includes(type) ? type : 'info';
            this.messaging.notify({
                message: message_is_html ? Markup(message) : message,
                sticky,
                title,
                type: (notificationType || 'info'),
            });
        },

        async _handleNotificationBannerNotificationOF(payload) {
            const container = document.querySelector("nav.o_main_navbar");
            if (!container) {
                return;
            }

            const banner = document.createElement("div");
            banner.className = `banner-notification banner-${payload.type}`;
            banner.innerHTML = `
            <div class="banner-header">
                <strong>${payload.title}</strong> ${payload.message_is_html ? payload.message : _.escape(payload.message)}
            </div>
            <div class="banner-button-close">
                <button type="button" class="close" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            `;
            container.insertAdjacentElement('afterend', banner);

            banner.querySelector('.close').addEventListener('click', () => {
                banner.style.animation = "fadeOut 0.5s ease-in-out";
                banner.addEventListener('animationend', () => {
                    banner.remove();
                });
            });
        }
    }
})
