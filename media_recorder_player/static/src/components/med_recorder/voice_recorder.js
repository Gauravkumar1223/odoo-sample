/** @odoo-module */
export default class VoiceRecorder {
    // Initialize state and other variables in the constructor or setup method.
    constructor() {
        this.isRecording = false;
        this.audioChunks = [];
        this.mediaRecorder = null;
        this.stream = null;
        this.socket = null;
        this.transcriptionText = '';

        // ...
    }

    // Method to handle the recording start.
    async startRecording() {
        console.log('Start recording invoked.');

        // Configure WebSocket for real-time transcription.
        const socketAddress = this.constructWebSocketAddress();
        this.socket = new WebSocket(socketAddress);

        // Define the audio constraints for the recording.
        const audioConstraints = {
            audio: {
                sampleRate: 16000,
                echoCancellation: true,
                output: false,
            },
        };

        try {
            // Get user media and create media recorder.
            const stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
            this.stream = stream;
            this.mediaRecorder = new MediaRecorder(stream);

            // Handle the data available after recording.
            this.handleRecorderData();

            // Start the media recorder with a timeslice (2-second chunks of data).
            this.mediaRecorder.start(2000);
            this.isRecording = true;

            // Set up WebSocket event listener for transcription messages.
            this.setupWebSocket();

            console.log('Recording started.');
        } catch (error) {
            console.error('Error starting recording:', error);
        }
    }

    // Method to handle the recording stop.
    async stopRecording() {
        console.log('Stop recording invoked.');

        this.mediaRecorder.stop();
        this.stream.getAudioTracks()[0].stop();
        this.isRecording = false;

        // Clean up WebSocket connection.
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }

        console.log('Recording stopped.');
    }

    // Method to construct WebSocket URL for real-time transcription.
    constructWebSocketAddress() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const port = protocol === 'wss:' ? '443' : '80';
        const path = 'custom_socket/realtime_transcribe';
        const address = `${protocol}//${location.hostname}:${port === '80' ? '' : port}/${path}`;
        return address;
    }

    // Method to handle data from the media recorder.
    handleRecorderData() {
        this.mediaRecorder.ondataavailable = (event) => {
            this.audioChunks.push(event.data);
            this.transmitAudioData(event.data);
        };

        this.mediaRecorder.onstop = async () => {
            await this.saveRecording();
        };
    }

    // Method to save the processed recording.
    async saveRecording() {
        const audioBlob = new Blob(this.audioChunks, {type: 'audio/wav'});
        console.log('Processing and saving recording.');
        // Handle saving the recording with your saveRecording method
        // ...
    }

    // Method to transmit the audio data to the WebSocket server.
    transmitAudioData(blobData) {
        const reader = new FileReader();
        reader.readAsDataURL(blobData);
        reader.onloadend = () => {
            const base64Data = reader.result;
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(base64Data);
            }
        };
    }

    // Method to set up WebSocket event listeners.
    setupWebSocket() {
        this.socket.onmessage = (event) => {
            try {
                const response = JSON.parse(event.data);
                if (response.type === 'Results') {
                    this.processTranscriptionResult(response);
                }
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };
    }

    // Method to process transcription results received via WebSocket.
    processTranscriptionResult(response) {
        const transcript = response?.channel?.alternatives?.[0]?.transcript;
        if (transcript) {
            this.transcriptionText += ` ${transcript.trim()}`;
            this.updateTranscriptionDisplay();
            console.log('Transcription updated:', this.transcriptionText);
        }
    }

    // Method to update the transcription display (e.g., a textarea on the page).
    updateTranscriptionDisplay() {
        const textarea = document.querySelector('textarea.wrr_custom_textarea');
        if (textarea) {
            textarea.textContent = this.transcriptionText;
            textarea.scrollTop = textarea.scrollHeight; // Scroll to the bottom
        }
    }

    // Method to toggle recording state.
    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    // Other methods as needed...
}


// End of class VoiceRecorder

