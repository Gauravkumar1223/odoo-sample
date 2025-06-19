/** @odoo-module */

import { registry } from "@web/core/registry"
import { Layout } from "@web/search/layout"
import { getDefaultConfig } from "@web/views/view"
import { useService } from "@web/core/utils/hooks"
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog"
import { routeToUrl } from "@web/core/browser/router_service"
import { browser } from "@web/core/browser/browser"


const { Component, useSubEnv, useState } = owl

export class OwlOdooServices extends Component {
    setup(){
        console.log("Owl Odoo Services")
        this.display = {
            controlPanel: {"top-right": false, "bottom-right": false}
        }

        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            }
        })

        this.cookieService = useService("cookie")
        console.log(this.cookieService)

        if (this.cookieService.current.dark_theme == undefined){
            this.cookieService.setCookie("dark_theme", false)
        }

        const router = this.env.services.router

        this.state = useState({
            transcript: "",
            language: "en-US",
            recording: false,
        })

        const titleService = useService("title")
        titleService.setParts({zopenerp: "Odoo", odoo: "Services", any:"frynol"})
        console.log(titleService.getParts())
        this.mediaRecorder = null;
        this.ws = null;
    }

    async startRecording(){

        this.ws = new WebSocket('ws://localhost:8080');
        this.ws.onopen = () => {
            console.log("Connected to the server.");
        };

        this.ws.onmessage = (e) => {
           this.state.transcript += e.data + " ";
        };

        this.ws.onerror = (err) => {
            console.error('Error occurred:', err.message);
        };

        this.ws.onclose = () => {
            console.log('Connection closed.');
            ws.send("close");
            this.ws.close();
            this.ws = null;
        }



        // Start recording
        this.state.recording = true;
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.mediaRecorder.start(3072);

            this.mediaRecorder.ondataavailable = (e) => {
                this.ws.send(e.data);
            };
        } catch (error) {
            console.error('Error starting recording:', error);
            this.state.recording = false;
            if (this.ws) {
                this.ws.close();
                this.ws = null;
            }
        }

    }

    async stopRecording() {
            // Ensure recording is stopped
    //

//            if (this.mediaRecorder && this.state.recording) {
//                // Stop the media recorder
//                this.mediaRecorder.stop();
//                // This event will be triggered one last time after stopping
//                this.mediaRecorder.ondataavailable = async (e) => {
//                    // Ensure there's data to send
//                    if (e.data.size > 0) {
//                        this.ws.send(e.data);
//                        console.log("Final chunk of data sent.");
//
//                        // Close the WebSocket connection after the final data is sent
//                        this.ws.close();
//                        this.ws = null;
//
//                        // Reset the media recorder
//                        this.mediaRecorder = null;
//
//                        // Stop all media tracks to release the microphone
//                        this.stream.getTracks().forEach(track => track.stop());
//                        this.stream = null;
//
//                        // Update recording state
//                        this.state.recording = false;
//                    }
//                };
//            } else {
////                // If recording is somehow already stopped, ensure WebSocket is closed
//                if (this.ws) {
//                    ws.send("close");
//                    this.ws.close();
//                    this.ws = null;
//                }
                // Ensure the recording state is set to false
                this.state.recording = false;
//            }
        }


}

OwlOdooServices.template = "owl.OdooServices"
OwlOdooServices.components = { Layout }

registry.category("actions").add("owl.OdooServices", OwlOdooServices)