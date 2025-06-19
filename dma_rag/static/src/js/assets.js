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
    }

    showNotification(message){
        const notification = this.env.services.notification
        notification.add(message, {
            title: "Odoo Notification Service",
            type: "info", //info, warning, danger, success
            sticky: true,
            className: "p-4",

        })
    }

    showDialog(){
        const dialog = this.env.services.dialog
        dialog.add(ConfirmationDialog, {
            title: "Dialog Service",
            body: "Are you sure you want to continue this action?",
            confirm: ()=>{
                console.log("Dialog Confirmed.")
            },
            cancel: ()=>{
                console.log("Dialog Cancelled")
            }
        }, {
            onClose: ()=> {
                console.log("Dialog service closed....")
            }
        })
        console.log(dialog)
    }

   async startRecording() {
        this.showNotification("Recording Started....");
        this.state.recording = true;

        // Request access to user's microphone
        navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
            console.log({ stream });

            // Check if browser supports the required audio format
            if (!MediaRecorder.isTypeSupported("audio/webm"))
                return alert("Browser not supported");

            // Create a MediaRecorder instance to capture audio
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: "audio/webm",
            });
            const url = "wss://api.deepgram.com/v1/listen?language=" + this.state.language;
            // Establish a WebSocket connection to Deepgram API for streaming audio
            const socket = new WebSocket(url, [
                "token",
                "4b9a25527a6cad07438a59e3a5b4699f26da4b84",
            ]);

            // Handle WebSocket events
            socket.onopen = () => {
                console.log("Connected to Deepgram");

                // Event listener for capturing audio data and sending it to the server
                mediaRecorder.addEventListener("dataavailable", async (event) => {
                    if (event.data.size > 0 && socket.readyState == 1) {
                        socket.send(event.data);
                    }
                });

                // Start recording audio with a specified time interval
                mediaRecorder.start(1000);
            };

            // Event listener for receiving transcription from the server
            socket.onmessage = (message) => {
                const received = JSON.parse(message.data);
                const transcript = received.channel.alternatives[0].transcript;
                if (transcript && received.is_final) {
                    console.log(transcript);
                    this.state.transcript += transcript + " ";
                }
            };

            // Event listener for WebSocket connection closure
            socket.onclose = (error) => {
                console.log("Connection closed", error);
            };

            // Event listener for WebSocket errors
            socket.onerror = (error) => {
                console.log("WebSocket error", error);
            };

            // Check if recording should stop
            const checkRecording = setInterval(() => {
                if (!this.state.recording) {
                    mediaRecorder.stop();
                    socket.close();
                    clearInterval(checkRecording);
                    console.log("Recording stopped due to state change.");
                }
            }, 1000); // Check every second
        });
    }


    async stopRecording() {
        this.showNotification("Recording Stopped")
        this.state.recording = false
    }


    async resetRecording() {
        this.showNotification("Recording Reset")
        this.state.transcript = ""
    }
    async startRecordingChunks() {
        navigator.mediaDevices.getUserMedia({ audio: { channelCount: 2, volume: 1.0, echoCancellation: false, noiseSuppression: false } }).then(function(stream) {
            const Recorder = new MediaRecorder(stream, { audioBitsPerSecond: 128000, mimeType: "audio/webm; codecs=opus" });
            Recorder.start(5000);
            Recorder.addEventListener("dataavailable", async function(event) {
                const audioBlob = new Blob([event.data], { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio_file', audioBlob, 'audio.mp3');
                formData.append('language', this.state.language);
                try {
                    const response = await fetch("/frynol_rag/recording/", {
                        method: "POST",
                        body: formData, // Send as FormData, not JSON
                    });
                    const data = await response.json();
                    console.log(data);
                    const current_transcript = data.data;
                    console.log(current_transcript,"----------current_transcript----------");
                    this.state.transcript = this.state.transcript + current_transcript;
                } catch (error) {
                    console.error('Error:', error);
                }
            });
        });
    }



    changeLanguage(event){
        this.state.language = event.target.value
        console.log(this.state.language,"--------------")
    }

}

OwlOdooServices.template = "owl.OdooServices"
OwlOdooServices.components = { Layout }

registry.category("actions").add("owl.OdooServices", OwlOdooServices)