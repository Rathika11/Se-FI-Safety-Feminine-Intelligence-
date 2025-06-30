# live_video_page.py
import streamlit as st
import os
import tempfile
import time
import shutil # Added for shutil.move

# Attempt to import necessary components for recording
# Define variables and classes outside the function, but move st calls inside
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
    from streamlit_webrtc.record import MediaRecorderBase
    import av # Required for PyAV for recording
    RECORDING_AVAILABLE = True

    # Define the MediaRecorder class only if imports are successful
    class MP4MediaRecorder(MediaRecorderBase):
        def __init__(self) -> None:
            self.output_path = ""
            self.__container: av.Container | None = None
            self.__output_file: tempfile._TemporaryFileWrapper | None = None

        def init_container(self) -> av.Container:
            self.__output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            self.output_path = self.__output_file.name
            options = {"vcodec": "libx264"} # Use libx264 codec
            try:
                self.__container = av.open(self.output_path, mode="w", format="mp4", options=options)
                # Moved st.info inside the main function or a method called later
                return self.__container
            except Exception as e:
                 # Moved st.error inside the main function or a method called later
                 self.__output_file.close()
                 if os.path.exists(self.output_path):
                      try: os.remove(self.output_path)
                      except: pass
                 raise

        def start_recording(self):
             pass # File opened in init_container

        def stop_recording(self):
            if self.__container:
                # Moved st.info inside the main function or a method called later
                try:
                    for stream in self.__container.streams:
                         if stream.codec_context:
                             while True:
                                 packet = stream.codec_context.encode()
                                 if not packet: break
                                 self.__container.mux(packet)
                    self.__container.close()
                    self.__container = None
                    self.__output_file.close()

                    final_dir = RECORDINGS_DIR
                    os.makedirs(final_dir, exist_ok=True)
                    timestamp = int(time.time())
                    base, ext = os.path.splitext(os.path.basename(self.output_path))
                    final_filename = f"recording_{timestamp}{ext}"
                    final_path = os.path.join(final_dir, final_filename)

                    try:
                        shutil.move(self.output_path, final_path)
                        # Moved st.success inside the main function or a method called later
                    except FileExistsError:
                         # Moved st.warning inside the main function or a method called later
                         timestamp_alt = int(time.time() * 1000)
                         final_filename_alt = f"{base}_{timestamp_alt}{ext}"
                         final_path_alt = os.path.join(final_dir, final_filename_alt)
                         try:
                              shutil.move(self.output_path, final_path_alt)
                              # Moved st.success inside the main function or a method called later
                         except Exception as alt_move_e:
                              # Moved st.error inside the main function or a method called later
                              pass # Error handled below

                    except Exception as move_e:
                        # Moved st.error inside the main function or a method called later
                        pass # Error handled below


                except Exception as e:
                    # Moved st.error inside the main function or a method called later
                    pass # Error handled below
                finally:
                     if os.path.exists(self.output_path):
                          try:
                               time.sleep(0.1) # Give move a moment
                               if os.path.exists(self.output_path):
                                   os.remove(self.output_path)
                                   # print message moved
                          except: pass

except ImportError:
    # Define dummies if recording components are not installed
    RECORDING_AVAILABLE = False
    # Moved st.error and st.info inside the main function

    class WebRtcMode:
        SENDRECV = None # Dummy
        RECVONLY = None # Dummy
    class MediaRecorderBase: # Dummy Base Class
        def __init__(self, *args, **kwargs): pass
        def init_container(self): pass
        def start_recording(self): pass
        def stop_recording(self): pass
    # Dummy webrtc_streamer
    def webrtc_streamer(*args, **kwargs):
        # Moved st.warning inside the main function
        class DummyWebRtcContext:
            def __init__(self):
                class DummyState:
                    playing = False
                    state = "STOPPED"
                self.state = DummyState()
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return DummyWebRtcContext()

    # Dummy recorder class (defined even if not used, for type hinting safety)
    class MP4MediaRecorder(MediaRecorderBase):
        def __init__(self, *args, **kwargs): pass
        def init_container(self): return None
        def start_recording(self): print("Dummy recorder start called")
        def stop_recording(self): print("Dummy recorder stop called")
    # Dummy av if not imported
    if 'av' not in locals(): av = None
    # Dummy shutil if not imported
    if 'shutil' not in locals():
        class DummyShutil:
            def move(self, src, dst): print(f"Dummy shutil.move called for {src} to {dst}")
        shutil = DummyShutil()


# Recordings directory
RECORDINGS_DIR = "recordings"
# Check if os is available before calling os.makedirs
if 'os' in locals() and hasattr(os, 'makedirs'):
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
else:
    print("Warning: os module not fully available, cannot create recordings directory.")


def live_video_page():
    # Moved all st calls inside this function

    st.title("🎥 Live Video Recording")

    # Display import error messages here, inside the function
    if not RECORDING_AVAILABLE:
        st.error("Recording is unavailable: 'streamlit-webrtc' recording components not installed correctly.")
        st.info("Please install with: pip install streamlit-webrtc opencv-python aiortc av")


    query_params = st.query_params
    sos_trigger_id = query_params.get("id", [None])[0]

    if st.session_state.get('sos_triggered', False):
        st.warning("SOS sequence activated. Live video streaming/recording started.")
        if st.session_state.get('last_known_location'):
             loc = st.session_state['last_known_location']
             if isinstance(loc, dict) and 'latitude' in loc:
                  st.info(f"Last known location: Lat {loc['latitude']}, Lon {loc['longitude']}")
             elif isinstance(loc, dict) and 'error' in loc:
                  st.error(f"Location error: {loc['error']}")
             else:
                  st.info("Location requested, but result is pending or unexpected.")

    st.write("Use this page to stream and record live video from your device's camera.")
    if RECORDING_AVAILABLE:
        st.info(f"Recordings will be saved in the '{RECORDINGS_DIR}' directory on the server running the app.")
        st.info("Make sure your browser tab remains open and active for streaming/recording to continue.")
    else:
        st.warning("Recording functionality is not available due to installation issues.")


    recorder_instance = MP4MediaRecorder() if RECORDING_AVAILABLE else None

    # If recording is not available, webrtc_streamer might still work for streaming,
    # but without the recorder. We pass None to in_recorder.
    ctx = webrtc_streamer(
        key=f"video_stream_{sos_trigger_id}" if sos_trigger_id else "video_stream_manual",
        mode=WebRtcMode.SENDRECV if RECORDING_AVAILABLE else WebRtcMode.RECVONLY, # Use SENDRECV if recording is possible
        media_constraints={"video": True, "audio": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        in_recorder=recorder_instance, # Provide recorder instance if available (will be None if not available)
        video_frame_callback=None
    )

    if ctx.state.playing:
         st.success("Camera active and stream running.")
         if RECORDING_AVAILABLE: st.info("Recording is in progress (look for browser indicators).")
         else: st.warning("Recording is not active.")
    elif ctx.state.state == "STOPPED":
         st.warning("Video stream stopped.")
    elif ctx.state.state == "READY":
         st.info("Click 'Start' below the video feed to begin stream (and recording if installed).")
    else:
         st.info("Waiting for camera...")

    st.markdown("---")

    st.subheader("Saved Recordings:")
    # Ensure the recordings directory exists before listing
    if 'os' in locals() and hasattr(os, 'path') and hasattr(os.path, 'exists') and os.path.exists(RECORDINGS_DIR) and hasattr(os, 'path') and hasattr(os.path, 'isdir') and os.path.isdir(RECORDINGS_DIR):
        if 'os' in locals() and hasattr(os, 'listdir'):
            recordings = [f for f in os.listdir(RECORDINGS_DIR) if f.endswith(".mp4")]
            try:
                 if 'os' in locals() and hasattr(os, 'path') and hasattr(os.path, 'join') and hasattr(os, 'path') and hasattr(os.path, 'getmtime'):
                      recordings.sort(key=lambda x: os.path.getmtime(os.path.join(RECORDINGS_DIR, x)), reverse=True)
                 else:
                      recordings.sort(reverse=True) # Fallback sort
            except:
                 recordings.sort(reverse=True) # Fallback sort


            if recordings:
                st.write(f"Found {len(recordings)} recording(s).")
                for recording in recordings:
                    file_path = os.path.join(RECORDINGS_DIR, recording)
                    try:
                        if 'open' in globals() and 'Exception' in globals(): # Check if basic functions are available
                            with open(file_path, "rb") as f:
                                 st.download_button(label=f"Download {recording}", data=f, file_name=recording, mime="video/mp4", key=f"download_{recording}")
                        else:
                             st.warning(f"Cannot offer download for {recording} due to missing functions.")

                    except Exception as e: st.error(f"Error reading file {recording}: {e}")

                st.markdown("---")
                st.subheader("Manage Recordings:")
                if st.button("Clear All Recordings", key="clear_recordings"):
                     count = 0
                     if 'os' in locals() and hasattr(os, 'remove'):
                         for recording in recordings:
                              file_path = os.path.join(RECORDINGS_DIR, recording)
                              try: os.remove(file_path); count += 1
                              except Exception as e: st.error(f"Error deleting file {recording}: {e}")
                         st.success(f"Cleared {count} recording(s).")
                         st.rerun()
                     else:
                         st.warning("Cannot clear recordings due to missing functions.")
            else: st.info("No recordings saved yet.")
        else: st.info("Cannot list recordings due to missing functions.")
    else: st.info("Recordings directory not found.")


    st.markdown("---")
    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard_video"):
        st.session_state.sos_triggered = False
        st.session_state.sos_pending_location = False
        st.session_state.last_known_location = None
        st.session_state.page = 'dashboard'
        st.rerun()

