/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

export class RealtimeTextarea extends Component {
    setup() {
        this.state = useState({
            textContent: "",
        });
        this.webSocket = null;
    }

    toggleStream() {
        if (this.webSocket) {
            clearInterval(this.randomNumberInterval);  // Clear the interval when closing the WebSocket
            this.webSocket.close();  // Close the existing WebSocket connection
            this.webSocket = null;
        } else {
            // Construct the WebSocket URL using the current server's hostname and the provided endpoint
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const hostname = window.location.hostname;
            const port = 9069;  // Update this to the actual WebSocket port
            const wsUrl = `${protocol}${hostname}:${port}/random_number`;
            this.webSocket = new WebSocket(wsUrl);

            this.webSocket.onopen = (event) => {
                console.log('WebSocket is open now.');
                // Set up an interval to send a random number every half a second
                this.randomNumberInterval = setInterval(() => {
                    this.sendRandomNumber();
                }, 500);
            };
            this.webSocket.onclose = (event) => {
                console.log('WebSocket is closed now.');
                clearInterval(this.randomNumberInterval);  // Clear the interval when the WebSocket is closed
            };
            this.webSocket.onerror = (event) => {
                console.error('WebSocket error observed:', event);
            };
            this.webSocket.onmessage = (event) => {
                this.state.textContent = event.data;  // Update the text content with the new data
            };
        }
    }

    sendRandomNumber() {
        const clientRandomNumber = Math.floor(Math.random() * 100);
        this.webSocket.send(clientRandomNumber.toString());
    }

    willUnmount() {
        // Close the WebSocket connection when the widget is unmounted
        if (this.webSocket) {
            this.webSocket.close();
        }
    }
}

RealtimeTextarea.template = "ai_wrrrit.RealtimeTextarea";

registry.category("fields").add("realtime_textarea", RealtimeTextarea);

export default RealtimeTextarea;
