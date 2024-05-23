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
            /**
             * Cette fonction récupère un message et le renvois dans la fonction qui traite ce type de message
             */
            if (message.type === "of_banner_notification") {
                return this._handleNotificationBannerNotificationOF(message.payload);
            }
            if (message.type === "of_simple_notification") {
                return this._handleNotificationSimpleNotificationOF(message.payload);
            }
            return this._super(message);
        },

        async _handleNotificationSimpleNotificationOF({ message, message_is_html, sticky, title, type, message_id }) {
            /**
             * Cette fonction récupère un message et crée une notification de type pop-up sur le haut droit de l'écran
             */
            let self = this;
            let notificationType = type
            notificationType = ["warning", "danger", "success", "info"].includes(type) ? type : 'info';

            this.messaging.notify({
                message: message_is_html ? Markup(message) : message,
                sticky,
                title,
                type: (notificationType || 'info'),
                close: () => console.log('YOUHOUUUU'),
            });
        },

        async _handleNotificationBannerNotificationOF(payload) {
            /**
             * Cette fonction récupère un message et crée une notification de type bannière sous la bare de navigation de odoo
             * Elle permet de vérifier si le message a été lue ou fermé
             */
            let self = this;

            const container = document.querySelector("nav.o_main_navbar");
            if (!container) {
                return;
            }

            const existingBanners = document.querySelectorAll('.banner-notification');
            if (existingBanners.length >= 3) {
                existingBanners[2].remove();
            }

            const banner = document.createElement("div");
            banner.className = `banner-notification banner-${payload.type}`;
            banner.innerHTML = `
            <div class="banner-header">
                <div class="bold">${payload.title}</div> ${payload.message_is_html ? payload.message : _.escape(payload.message)}
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

            banner.querySelector('.see_later').addEventListener('click', () => {
                banner.style.animation = "fadeOut 0.5s ease-in-out";
                banner.addEventListener('animationend', () => {
                    banner.remove();
                });
            });

            const closeButton = document.querySelector('.banner-button-close button');
            const headerLink = document.querySelector('.banner-header a');

            if (closeButton) {
                closeButton.addEventListener('click', async function() {
                    await recordNotificationRead(payload.message_id, 'close');
                });
            }

            if (headerLink) {
                headerLink.addEventListener('click', async function() {
                    await recordNotificationRead(payload.message_id, 'view');
                });
            }

            async function recordNotificationRead(messageId, actionType) {
                await self.messaging.rpc({
                    model: 'of.communication.notification.log',
                    method: 'mark_msg_as_read',
                    args: [messageId, actionType]
                }, { shadow: true });
            }
        },
    }
})
