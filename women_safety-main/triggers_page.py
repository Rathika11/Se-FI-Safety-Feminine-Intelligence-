# triggers_page.py
import streamlit as st
import streamlit.components.v1 as components

def voice_trigger_component():
    """
    Creates a Streamlit component that uses the Web Speech API for voice recognition
    and Web Audio API for sound detection.
    Returns the value sent from the JavaScript component.
    """
    # JavaScript code for speech recognition and sound detection
    speech_recognition_js = """
    <script>
        console.log("Voice and sound trigger component script loaded.");

        // Function to send message to Streamlit
        function sendMessageToStreamlit(message) {
            console.log("Sending message to Streamlit:", message);
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: message
            }, "*");
        }

        // Initialize speech recognition and sound detection
        function initRecognition() {
            console.log("Initializing recognition systems.");
            const recognitionDiv = document.getElementById('recognition-status');
            const startButton = document.getElementById('start-recognition');
            const stopButton = document.getElementById('stop-recognition');
            const statusDiv = document.getElementById('status-message');
            const transcriptSpan = document.getElementById('transcript');
            const soundLevelMeter = document.getElementById('sound-level-meter');
            const soundLevelValue = document.getElementById('sound-level-value');
            
            // Variable to track if we've already triggered an alert
            let alertTriggered = false;
            
            // Reset alert after some time to allow new alerts
            function resetAlertTrigger() {
                setTimeout(() => {
                    alertTriggered = false;
                    console.log("Alert system reset and ready for new triggers");
                }, 10000); // Reset after 10 seconds
            }

            // PART 1: SPEECH RECOGNITION SETUP
            // Check if browser supports speech recognition
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                statusDiv.innerHTML = "Speech recognition not supported in this browser. Try Chrome or Edge.";
                startButton.disabled = true;
                console.error("Speech recognition not supported.");
                return;
            }

            // Initialize speech recognition
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();

            recognition.continuous = true; // Keep listening
            recognition.interimResults = true; // Get interim results for faster response
            recognition.lang = 'en-US'; // Set language

            let isRecognizing = false;

            // Recognition results
            recognition.onresult = (event) => {
                // Get the transcript from the last result
                const lastResultIndex = event.results.length - 1;
                const transcript = event.results[lastResultIndex][0].transcript.trim().toLowerCase();

                console.log("Transcript:", transcript);
                transcriptSpan.textContent = transcript;

                // Check for trigger words - making it more flexible with partial matches
                if (!alertTriggered && (
                    transcript.includes('help') || 
                    transcript.includes('danger') || 
                    transcript.includes('emergency') || 
                    transcript.includes('sos')
                )) {
                    const triggerWord = 
                        transcript.includes('help') ? 'help' : 
                        transcript.includes('danger') ? 'danger' : 
                        transcript.includes('emergency') ? 'emergency' : 'sos';
                        
                    statusDiv.innerHTML = `<strong>ALERT:</strong> Detected trigger word "${triggerWord}"!`;
                    console.log("Trigger word detected:", triggerWord);
                    
                    // Set flag to prevent multiple rapid triggers
                    alertTriggered = true;
                    
                    // Send message to Streamlit
                    sendMessageToStreamlit({
                        'action': 'trigger',
                        'keyword': triggerWord,
                        'transcript': transcript,
                        'source': 'voice'
                    });
                    
                    // Reset alert trigger after delay
                    resetAlertTrigger();
                }
            };

            // Handle speech recognition errors
            recognition.onerror = (event) => {
                console.error("Recognition error:", event.error);
                statusDiv.innerHTML = `Error: ${event.error}`;
                isRecognizing = false;
                startButton.disabled = false;
                stopButton.disabled = true;
                recognitionDiv.className = "recognition-container recognition-inactive";
                
                // Try to restart after errors
                setTimeout(() => {
                    try {
                        if (!isRecognizing) {
                            recognition.start();
                            isRecognizing = true;
                            statusDiv.innerHTML = "Listening for commands...";
                            startButton.disabled = true;
                            stopButton.disabled = false;
                            recognitionDiv.className = "recognition-container recognition-active";
                        }
                    } catch (e) {
                        console.error("Failed to restart after error:", e);
                    }
                }, 2000);
            };

            // Handle end of recognition
            recognition.onend = () => {
                console.log("Recognition ended.");
                // If recognition ends but we intended it to be continuous, try restarting
                if (recognition.continuous && isRecognizing) {
                    console.log("Recognition ended unexpectedly, attempting restart.");
                    try {
                         recognition.start();
                         statusDiv.innerHTML = "Listening for commands...";
                         recognitionDiv.className = "recognition-container recognition-active";
                    } catch (e) {
                         console.error("Error restarting recognition:", e);
                         statusDiv.innerHTML = `Error restarting recognition: ${e.message}`;
                         isRecognizing = false;
                         startButton.disabled = false;
                         stopButton.disabled = true;
                         recognitionDiv.className = "recognition-container recognition-inactive";
                    }
                } else {
                    statusDiv.innerHTML = "Voice detection stopped";
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    recognitionDiv.className = "recognition-container recognition-inactive";
                }
            };

            // PART 2: SOUND DETECTION SETUP
            // Initialize audio context and analyzer for sound detection
            let audioContext;
            let analyser;
            let microphone;
            let javascriptNode;
            let soundDetectionActive = false;
            
            // Sound threshold for loud noise detection (adjust as needed)
            const SOUND_THRESHOLD = 60; // Lower is more sensitive, higher is less sensitive
            
            // Initialize sound detection
            async function initSoundDetection() {
                try {
                    // Create audio context
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    
                    // Get microphone access
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    
                    // Create analyzer
                    analyser = audioContext.createAnalyser();
                    analyser.fftSize = 256;
                    analyser.smoothingTimeConstant = 0.3;
                    
                    // Connect microphone to analyzer
                    microphone = audioContext.createMediaStreamSource(stream);
                    microphone.connect(analyser);
                    
                    // Setup javascript processing node
                    javascriptNode = audioContext.createScriptProcessor(1024, 1, 1);
                    analyser.connect(javascriptNode);
                    javascriptNode.connect(audioContext.destination);
                    
                    // Process audio data
                    javascriptNode.onaudioprocess = function() {
                        if (!soundDetectionActive) return;
                        
                        const array = new Uint8Array(analyser.frequencyBinCount);
                        analyser.getByteFrequencyData(array);
                        
                        // Calculate average volume
                        let average = 0;
                        for (let i = 0; i < array.length; i++) {
                            average += array[i];
                        }
                        average /= array.length;
                        
                        // Update sound level meter
                        const levelPercentage = Math.min(100, average * 2); // Scale for better visual
                        soundLevelMeter.style.width = levelPercentage + '%';
                        soundLevelValue.textContent = Math.round(average);
                        
                        // Check if sound is above threshold
                        if (!alertTriggered && average > SOUND_THRESHOLD) {
                            console.log("Loud sound detected:", average);
                            statusDiv.innerHTML = `<strong>ALERT:</strong> Detected loud sound (${Math.round(average)})!`;
                            
                            // Set flag to prevent multiple rapid triggers
                            alertTriggered = true;
                            
                            // Send message to Streamlit
                            sendMessageToStreamlit({
                                'action': 'trigger',
                                'keyword': 'loud_sound',
                                'level': average,
                                'source': 'sound'
                            });
                            
                            // Reset alert trigger after delay
                            resetAlertTrigger();
                        }
                    };
                    
                    soundDetectionActive = true;
                    console.log("Sound detection initialized successfully");
                    
                } catch (error) {
                    console.error("Error initializing sound detection:", error);
                    statusDiv.innerHTML += "<br>Failed to initialize sound detection: " + error.message;
                }
            }
            
            // Start button event
            startButton.addEventListener('click', async () => {
                console.log("Start button clicked.");
                if (!isRecognizing) {
                    try {
                        // Start voice recognition
                        recognition.start();
                        isRecognizing = true;
                        
                        // Initialize sound detection if not already done
                        if (!soundDetectionActive) {
                            await initSoundDetection();
                        }
                        
                        statusDiv.innerHTML = "Listening for commands and sounds...";
                        startButton.disabled = true;
                        stopButton.disabled = false;
                        recognitionDiv.className = "recognition-container recognition-active";
                        console.log("Recognition systems started.");
                    } catch (e) {
                        console.error("Error starting recognition:", e);
                        statusDiv.innerHTML = `Error starting recognition: ${e.message}`;
                    }
                }
            });

            // Stop button event
            stopButton.addEventListener('click', () => {
                console.log("Stop button clicked.");
                if (isRecognizing) {
                    recognition.stop();
                    isRecognizing = false;
                    soundDetectionActive = false;
                    statusDiv.innerHTML = "Detection systems stopped";
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    recognitionDiv.className = "recognition-container recognition-inactive";
                    console.log("Recognition stopped.");
                }
            });

            // Initialize button states
            startButton.disabled = false;
            stopButton.disabled = true;
            
            // AUTO-START both recognition systems when component loads
            setTimeout(async () => {
                try {
                    console.log("Auto-starting recognition systems...");
                    
                    // Start voice recognition
                    recognition.start();
                    isRecognizing = true;
                    
                    // Initialize sound detection
                    await initSoundDetection();
                    
                    statusDiv.innerHTML = "Listening for commands and sounds...";
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    recognitionDiv.className = "recognition-container recognition-active";
                    console.log("Auto-start recognition successful.");
                } catch (e) {
                    console.error("Error auto-starting recognition:", e);
                    statusDiv.innerHTML = `Error starting automatic detection: ${e.message}. Please click 'Start Listening' manually.`;
                }
            }, 1000); // 1 second delay before auto-starting
        }

        // Initialize when document is loaded
        window.onload = initRecognition;
        console.log("Added window.onload listener for initRecognition.");

    </script>

    <style>
        /* Enhanced styling for better UI */
        .recognition-container {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            font-family: sans-serif;
            background-color: #f9f9f9; /* Light background */
        }

        .recognition-active {
            border-color: #4CAF50; /* Green border when active */
            box-shadow: 0 0 5px rgba(76, 175, 80, 0.5);
        }

        .recognition-inactive {
            border-color: #ddd; /* Default border when inactive */
        }

        .button-container {
            margin-top: 10px;
            display: flex;
            gap: 10px;
        }

        .start-button {
            background-color: #4CAF50; /* Green */
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .start-button:hover:not(:disabled) {
             background-color: #388E3C; /* Darker green on hover */
        }

        .stop-button {
            background-color: #f44336; /* Red */
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

         .stop-button:hover:not(:disabled) {
             background-color: #D32F2F; /* Darker red on hover */
        }

        .start-button:disabled, .stop-button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
            opacity: 0.6;
        }

        .status {
            margin-top: 10px;
            font-size: 14px;
            color: #333;
        }

        .transcript {
            margin-top: 10px;
            padding: 8px;
            background-color: #eee; /* Light grey background */
            border-radius: 4px;
            min-height: 20px; /* Ensure some height even when empty */
            font-style: italic;
            color: #666;
            word-wrap: break-word; /* Prevent overflow */
        }
        
        /* Sound level meter styling */
        .sound-level-container {
            margin-top: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #eee;
            height: 20px;
            position: relative;
        }
        
        .sound-level-bar {
            height: 100%;
            width: 0%;
            background-color: #2196F3;
            border-radius: 4px;
            transition: width 0.1s ease-in-out;
        }
        
        .sound-level-text {
            position: absolute;
            top: 0;
            left: 5px;
            right: 5px;
            line-height: 20px;
            color: #333;
            font-size: 12px;
            text-align: center;
        }
    </style>

    <div class="recognition-container" id="recognition-status">
        <h3>🎤 Voice & Sound Detection</h3>
        <p>Say <strong>"help"</strong>, <strong>"danger"</strong>, <strong>"emergency"</strong> or <strong>"SOS"</strong> OR make any loud sound to activate the SOS alert</p>
        <p><strong>Automatic detection is ACTIVE</strong> - no need to press any buttons</p>

        <div class="button-container">
            <button id="start-recognition" class="start-button">Start Listening</button>
            <button id="stop-recognition" class="stop-button" disabled>Stop Listening</button>
        </div>

        <div class="status" id="status-message">Initializing detection systems...</div>

        <div class="transcript">
            Last heard: <span id="transcript"></span>
        </div>
        
        <div class="sound-level-container">
            <div class="sound-level-bar" id="sound-level-meter"></div>
            <div class="sound-level-text">Sound Level: <span id="sound-level-value">0</span></div>
        </div>
    </div>
    """
    # Use the HTML component with a specified height, increased for the additional UI elements
    component_value = components.html(speech_recognition_js, height=380)

    # Return the value received from the component
    return component_value


# Define the voice_trigger_ui function (it calls voice_trigger_component)
def voice_trigger_ui():
    """
    Displays the voice and sound trigger UI in a Streamlit app and processes its output.
    """
    # Initialize session state for trigger data if it doesn't exist
    if 'voice_trigger_data' not in st.session_state:
        st.session_state.voice_trigger_data = None

    # Display the recognition component and get its return value
    component_value = voice_trigger_component()

    # --- Debug print to see what value is received ---
    print(f"voice_trigger_ui received component_value: {component_value}")
    # --- End debug print ---

    # Process component data
    # The component sends a dictionary when a trigger word or sound is detected
    if component_value is not None and isinstance(component_value, dict) and component_value.get('action') == 'trigger':
        # A trigger was detected by the JavaScript
        source = component_value.get('source', 'unknown')
        keyword = component_value.get('keyword', 'unknown')
        
        print(f"Streamlit detected trigger action from component: {component_value}") # Debug print
        
        # Set trigger flag and additional info in session state
        st.session_state.trigger_sos = True
        st.session_state.trigger_source = source
        st.session_state.trigger_keyword = keyword
        
        if source == 'voice':
            transcript = component_value.get('transcript', '')
            st.session_state.trigger_transcript = transcript
        elif source == 'sound':
            level = component_value.get('level', 0)
            st.session_state.trigger_sound_level = level
            
        st.rerun()  # Trigger rerun immediately


# Define the main triggers_page function (it calls voice_trigger_ui)
def triggers_page():
    st.title("📱 Triggers")

    st.write("This page is for configuring different methods to automatically activate the SOS alert.")
    
    # Add a notice about auto-activation
    st.success("🎤 Voice & sound detection starts automatically when you open this page. Say **'help'**, **'danger'**, **'emergency'**, **'SOS'** or make any **loud noise** to activate the SOS alert.")

    # Voice/sound trigger section
    trigger_tab, other_triggers_tab = st.tabs(["🎤 Voice & Sound Triggers", "📲 Other Triggers"])

    with trigger_tab:
        st.subheader("Voice & Sound Triggers")
        st.write("Automatically trigger the SOS alert by voice commands or loud sounds.")

        # Initialize session state variables if they don't exist
        if 'trigger_sos' not in st.session_state:
            st.session_state.trigger_sos = False
        if 'trigger_source' not in st.session_state:
            st.session_state.trigger_source = None
        if 'trigger_keyword' not in st.session_state:
            st.session_state.trigger_keyword = None

        # Handle automatic SOS trigger if detected
        if st.session_state.get('trigger_sos', False):
            # Determine type of trigger for custom message
            source = st.session_state.get('trigger_source', 'unknown')
            keyword = st.session_state.get('trigger_keyword', 'unknown')
            
            # Show appropriate alert based on trigger source
            if source == 'voice':
                transcript = st.session_state.get('trigger_transcript', '')
                st.error(f"⚠️ EMERGENCY DETECTED - SOS ALERT ACTIVATED\n\nTriggered by voice: '{keyword}' detected in '{transcript}'")
            elif source == 'sound':
                level = st.session_state.get('trigger_sound_level', 0)
                st.error(f"⚠️ EMERGENCY DETECTED - SOS ALERT ACTIVATED\n\nTriggered by loud sound (level: {level:.1f})")
            else:
                st.error("⚠️ EMERGENCY DETECTED - SOS ALERT ACTIVATED")
                
            # Reset the trigger immediately after displaying the alert
            st.session_state.trigger_sos = False
            # In a real implementation, you would trigger the actual SOS alert function here
            # from dashboard import trigger_sos_alert_sequence
            # trigger_sos_alert_sequence()

        # Display the trigger UI component and handle its output
        voice_trigger_ui()

        with st.expander("Voice & Sound Detection Help"):
            st.markdown("""
            ### Voice Commands
            - Voice detection starts **automatically** when you open this page.
            - Say any of these words clearly to automatically trigger the SOS alert:
              - **"help"**
              - **"danger"**
              - **"emergency"**
              - **"SOS"**
            
            ### Sound Detection
            - The system will also listen for **loud sounds** like screams, crashes, or other noises that might indicate an emergency.
            - The sound level meter shows current audio input levels.
            
            ### Important Notes
            - Detection requires microphone permission from your browser.
            - Works best in Chrome or Edge browsers.
            - **The detection only works when the browser tab is active and in the foreground.**
            - If automatic detection isn't working, try clicking the "Start Listening" button manually.
            """)


    with other_triggers_tab:
        st.subheader("Conceptual Trigger Ideas:")

        # Add the sound-based trigger idea
        st.markdown("- **Sound Detection:** ✅ **IMPLEMENTED** - Automatically trigger the SOS alert when the device's microphone detects loud noises.")

        st.markdown("- **Hardware Button:** Integration with a physical panic button or wearable device (requires device-specific APIs and connection methods, complex for web).")
        st.markdown("- **Gesture Recognition:** Using device sensors (accelerometer/gyroscope if browser/OS allows access in background) or camera (less reliable for background triggers).")
        st.markdown("- **Voice Command:** ✅ **IMPLEMENTED** - Listening for specific keywords to trigger the alert.")
        st.markdown("- **Shake Detection:** Using accelerometer data (requires device sensor access and background processing).")
        st.markdown("- **Location-Based Triggers:** Automatically alerting when entering/leaving specific areas (requires continuous background location access).")

        st.info("For safety features requiring continuous background monitoring or direct device hardware access, a native mobile application is generally a more suitable platform than a standard web application.")

    st.markdown("---")
    # General note about web limitations
    st.warning("⚠️ Note: Due to browser limitations, automated triggers like voice commands or sound detection can only function while the app is open in an **active browser tab**.")

    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_triggers_bottom"):
        st.session_state.page = 'dashboard'
        st.rerun()