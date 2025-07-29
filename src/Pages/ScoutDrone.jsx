import React, { useEffect, useState, useRef } from 'react';
import '../assets/CSS/Scout.css'; // Assuming this path is correct for existing styles

const ScoutDrone = () => {
  const [isDark, setIsDark] = useState(false);
  const [activePane, setActivePane] = useState('crops');
  const [terminalOutput, setTerminalOutput] = useState('Ready to process AI detection...');
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [missionLoading, setMissionLoading] = useState(false);
  const [uploadingKML, setUploadingKML] = useState(false);
  const [kmlUploadMessage, setKmlUploadMessage] = useState('');
  const [flightParams, setFlightParams] = useState({
    line_spacing: 20,
    flight_altitude: 30,
    flight_velocity: 4.0,
    fence_buffer: 5,
    optimize_angle: true,
    angle: 90
  });
  // Changed from showDroneControlDrawer to showDroneControlModal
  const [showDroneControlModal, setShowDroneControlModal] = useState(false);

  const fileInputRef = useRef(null);
  const terminalRef = useRef(null);
  const mapFrameRef = useRef(null);

  // Auto-scroll terminal to bottom when new output is added
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalOutput]);

  // Fetch AI processed images from your backend
  useEffect(() => {
    fetchAIImages();
  }, []);

  // Toggle dark mode class on body
  useEffect(() => {
    if (isDark) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }
  }, [isDark]);

  // Function to append messages to the terminal output
  const appendToTerminal = (message) => {
    setTerminalOutput(prev => prev + '\n' + message);
  };

  // Fetches AI processed images from the backend
  const fetchAIImages = async () => {
    try {
      const response = await fetch('http://127.0.0.1:9080/ai-images');
      const data = await response.json();
      const formatted = data.imageUrls.map(name =>
        `http://127.0.0.1:9080/ai-images/${name}`
      );
      setImages(formatted);
    } catch (error) {
      console.error('Error fetching AI images:', error);
      appendToTerminal('❌ Error loading AI images. Please check connection.');
    }
  };

  // Runs the AI detection script on the backend
  const runAIScript = async () => {
    setLoading(true);
    appendToTerminal('🚀 Initializing AI processing...\n');

    try {
      const response = await fetch('http://127.0.0.1:9080/run-ai-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const result = await response.json();

      if (result.status === 'success') {
        appendToTerminal('✅ AI processing completed successfully!\n' + result.output);
        // Refresh images after processing
        setTimeout(() => {
          fetchAIImages();
        }, 2000);
      } else {
        appendToTerminal('❌ AI processing failed: ' + result.message);
      }
    } catch (error) {
      appendToTerminal('❌ Error running AI script: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Reloads AI data from the backend
  const reloadAIData = async () => {
    appendToTerminal('🔄 Reloading AI data...');
    try {
      const response = await fetch('http://127.0.0.1:9080/reload-ai-data', {
        method: 'POST'
      });
      const result = await response.json();
      appendToTerminal('✅ AI data reloaded successfully');
      fetchAIImages();
    } catch (error) {
      appendToTerminal('❌ Error reloading data: ' + error.message);
    }
  };

  // Sends a mission start command to the backend
  const startMission = async () => {
    setMissionLoading(true);
    appendToTerminal('🎯 Starting mission...\n');

    try {
      const response = await fetch('http://127.0.0.1:9080/send_mission_command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'mission_start' })
      });

      const result = await response.json();

      if (result.status === 'success') {
        appendToTerminal('✅ Mission started successfully!\n' + result.message);
      } else {
        appendToTerminal('❌ Mission start failed: ' + result.message);
      }
    } catch (error) {
      appendToTerminal('❌ Error starting mission: ' + error.message);
    } finally {
      setMissionLoading(false);
    }
  };

  // Fetches detailed information for a detected image
  const fetchImageInfo = async (imageName, overlayRef) => {
    if (overlayRef.dataset.loaded === "true") return;

    try {
      const response = await fetch(`http://127.0.0.1:9080/get-image-info/${imageName}`);
      const data = await response.json();

      overlayRef.dataset.loaded = "true";
      overlayRef.innerHTML = Object.keys(data).length === 0
        ? '<div class="no-data">No detection data available</div>'
        : Object.entries(data)
          .filter(([key]) => key !== 'Crop Path') // Hide internal paths
          .map(([key, value]) => {
            const displayKey = key.replace(/_/g, ' ').toUpperCase();
            return `<div class="info-row"><span class="key">${displayKey}:</span> <span class="value">${value}</span></div>`;
          })
          .join('');
    } catch (error) {
      overlayRef.innerHTML = '<div class="error">Failed to load detection info</div>';
    }
  };

  // Map control functions: show all markers
  const handleShowAll = () => {
    appendToTerminal('📍 Showing all detections on map...');
    // Send message to iframe to show all markers
    if (mapFrameRef.current) {
      mapFrameRef.current.contentWindow.postMessage({
        action: 'showAll'
      }, '*');
    }
  };

  // Map control functions: center the map view
  const handleCenterView = () => {
    appendToTerminal('🎯 Centering map view...');
    // Send message to iframe to center the view
    if (mapFrameRef.current) {
      mapFrameRef.current.contentWindow.postMessage({
        action: 'centerView'
      }, '*');
    }
  };

  // Handles changes in flight parameters form
  const handleParamChange = (paramName, value) => {
    setFlightParams(prev => ({
      ...prev,
      [paramName]: paramName === 'optimize_angle' ? value : (isNaN(value) ? value : Number(value))
    }));
  };

  // Handles file selection for KML upload
  const handleFileChange = (event) => {
    const files = Array.from(event.target.files);
    setSelectedFiles(files);
    setKmlUploadMessage(files.length > 0 ? `${files.length} file(s) selected.` : '');
  };

  // Handler for drag over event on the modal drop zone
  const handleDragOver = (event) => {
    event.preventDefault(); // Prevent default to allow drop
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'copy'; // Visual feedback
  };

  // Handler for drop event on the modal drop zone
  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const files = Array.from(event.dataTransfer.files).filter(file => file.name.endsWith('.kml'));
    setSelectedFiles(files);
    setKmlUploadMessage(files.length > 0 ? `${files.length} KML file(s) selected.` : 'No KML files dropped.');
  };

  // Uploads selected KML files to the backend and sends ROS2 messages
  const uploadKMLFiles = async () => {
    if (selectedFiles.length === 0) {
      setKmlUploadMessage('Please select KML files to upload.');
      return;
    }

    setUploadingKML(true);
    setKmlUploadMessage('Uploading KML files...');
    appendToTerminal('⬆️ Starting KML file upload...');

    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('kmlFiles', file); // 'kmlFiles' is the field name the backend expects
    });

    try {
      const uploadResponse = await fetch('http://127.0.0.1:9080/upload-kml', {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error(`KML upload failed: ${uploadResponse.statusText}`);
      }

      const uploadResult = await uploadResponse.json();
      appendToTerminal(`✅ KML upload successful: ${uploadResult.message}`);
      setKmlUploadMessage('KML files uploaded successfully!');

      // After successful upload, send message to ROS2 topic for each uploaded file
      for (const filename of uploadResult.uploadedFileNames) {
        appendToTerminal(`Sending ROS2 message for KML: ${filename}...`);
        try {
          const ros2Response = await fetch('http://127.0.0.1:9080/generate_waypoint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              filename: filename,
              params: {
                ...flightParams,
                kml_file: filename
              }
            }),
          });

          if (!ros2Response.ok) {
            throw new Error(`Failed to send ROS2 message for ${filename}: ${ros2Response.statusText}`);
          }
          const ros2Result = await ros2Response.json();
          appendToTerminal(`✅ ROS2 message sent for ${filename}: ${ros2Result.status}`);
        } catch (ros2Error) {
          appendToTerminal(`❌ Error sending ROS2 message for ${filename}: ${ros2Error.message}`);
        }
      }

      // Close modal and clear selected files after successful upload and message send
      setShowUploadModal(false);
      setSelectedFiles([]);
    } catch (error) {
      appendToTerminal(`❌ KML upload failed: ${error.message}`);
      setKmlUploadMessage(`Upload failed: ${error.message}`);
    } finally {
      setUploadingKML(false);
    }
  };

  // Function to send drone control commands to the backend
  const sendDroneCommand = async (command) => {
    appendToTerminal(`Sending drone command: ${command}...`);
    try {
      const response = await fetch('http://127.0.0.1:9080/send_mission_command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command })
      });
      const result = await response.json();
      if (result.status === 'success') {
        appendToTerminal(`✅ Drone command '${command}' successful: ${result.message}`);
      } else {
        appendToTerminal(`❌ Drone command '${command}' failed: ${result.message}`);
      }
    } catch (error) {
      appendToTerminal(`❌ Error sending drone command '${command}': ${error.message}`);
    }
  };

  return (
    <div className={`ai-page ${isDark ? 'dark-mode' : ''}`}>
      <div className="header">
        <div className="logo-section">
          <div className="logo-placeholder">AI</div>
          <h1 className="heading">Scout Drone</h1>
        </div>

        <div className="control-section">
          <div className="action-buttons">
            

            <button
              className="action-btn secondary"
              onClick={reloadAIData}
            >
              🔄 Refresh Data
            </button>
            <button
              className={`upload-kml-btn ${isDark ? 'dark' : 'light'}`}
              onClick={() => setShowUploadModal(true)}
            >
              ⬆️ Upload KML
            </button>
            <button
              className={`action-btn mission ${missionLoading ? 'loading' : ''}`}
              onClick={startMission}
              disabled={missionLoading}
            >
              {missionLoading ? '⏳ Starting...' : '🎯 Start Mission'}
            </button>
            {/* Button to open the drone control modal */}
            <button
              className={`action-btn control-drone ${isDark ? 'dark' : 'light'}`}
              onClick={() => setShowDroneControlModal(true)}
            >
              ⚙️ Drone Control
            </button>
          </div>

          <div className="nav-buttons">
            <button
              className={`nav-btn ${activePane === 'crops' ? 'active' : ''}`}
              onClick={() => setActivePane('crops')}
            >
              📸 Detections
            </button>

            <button
              className={`nav-btn ${activePane === 'map' ? 'active' : ''}`}
              onClick={() => setActivePane('map')}
            >
              🗺️ Map View
            </button>
          </div>

          <div className="theme-toggle">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={isDark}
                onChange={() => setIsDark(!isDark)}
              />
              <span className="slider">
                <span className="slider-icon">{isDark ? '🌙' : '☀️'}</span>
              </span>
            </label>
          </div>
        </div>
      </div>

      <div className="main-content">
        <div className="terminal-section">
          <div className="terminal-header">
            <div className="terminal-controls">
              <span className="control red"></span>
              <span className="control yellow"></span>
              <span className="control green"></span>
            </div>
            <span className="terminal-title">AI Processing Console</span>
          </div>
          <div className="terminal" ref={terminalRef}>
            <pre>{terminalOutput}</pre>
          </div>
        </div>

        <div className="content-section">
          {activePane === 'crops' && (
            <div className="gallery-container">
              <div className="gallery-header">
                <h2>Detected Objects ({images.length})</h2>
                <div className="gallery-stats">
                  <span className="stat-item">
                    📊 Total Detections: {images.length}
                  </span>
                </div>
              </div>

              <div className="gallery">
                {images.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon">🔍</div>
                    <h3>No Detections Yet</h3>
                    <p>Run AI detection to see processed objects here</p>
                  </div>
                ) : (
                  images.map((imageUrl, index) => {
                    const imageName = imageUrl.split('/').pop();
                    return (
                      <div
                        key={index}
                        className="detection-card"
                        data-name={imageName}
                        onMouseEnter={(e) => {
                          const overlay = e.currentTarget.querySelector('.detection-overlay');
                          fetchImageInfo(imageName, overlay);
                        }}
                      >
                        <div className="detection-image">
                          <img src={imageUrl} alt={`Detection ${index + 1}`} />
                          <div className="detection-badge">#{index + 1}</div>
                        </div>
                        <div className="detection-overlay" data-loaded="false">
                          <div className="loading-spinner">Loading detection data...</div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {activePane === 'map' && (
            <div className="map-container">
              <div className="map-header">
                <h2>🗺️ Geospatial Mapping</h2>
                <div className="map-controls">
                  <button className="map-btn" onClick={handleShowAll}>
                    📍 Show All
                  </button>
                  <button className="map-btn" onClick={handleCenterView}>
                    🎯 Center View
                  </button>
                </div>
              </div>
              <div className="map-frame">
                <iframe
                  ref={mapFrameRef}
                  src="http://127.0.0.1:9080/ai-map"
                  width="100%"
                  height="100%"
                  style={{ border: 'none', borderRadius: '6px' }}
                  title="AI Detection Map"
                ></iframe>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* KML Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay">
          <div className={`modal-content ${isDark ? 'dark' : 'light'}`}>
            <h3 className="modal-title">Upload KML Files & Configure Flight Parameters</h3>
            <p className="modal-description">Select KML files and configure flight parameters below.</p>

            {/* Flight Parameters Form */}
            <div className="params-form">
              <h4 className="params-title">Flight Parameters</h4>
              <div className="params-grid">

                <div className="param-group">
                  <label className="param-label">Line Spacing (m)</label>
                  <input
                    type="number"
                    className="param-input"
                    value={flightParams.line_spacing}
                    onChange={(e) => handleParamChange('line_spacing', e.target.value)}
                  />
                </div>
                <div className="param-group">
                  <label className="param-label">Flight Altitude (m)</label>
                  <input
                    type="number"
                    className="param-input"
                    value={flightParams.flight_altitude}
                    onChange={(e) => handleParamChange('flight_altitude', e.target.value)}
                  />
                </div>
                <div className="param-group">
                  <label className="param-label">Flight Velocity (m/s)</label>
                  <input
                    type="number"
                    step="0.1"
                    className="param-input"
                    value={flightParams.flight_velocity}
                    onChange={(e) => handleParamChange('flight_velocity', e.target.value)}
                  />
                </div>
                <div className="param-group">
                  <label className="param-label">Fence Buffer (m)</label>
                  <input
                    type="number"
                    className="param-input"
                    value={flightParams.fence_buffer}
                    onChange={(e) => handleParamChange('fence_buffer', e.target.value)}
                  />
                </div>
                <div className="param-group">
                  <label className="param-label">Angle (degrees)</label>
                  <input
                    type="number"
                    className="param-input"
                    value={flightParams.angle}
                    onChange={(e) => handleParamChange('angle', e.target.value)}
                  />
                </div>
                <div className="param-group checkbox-group">
                  <label className="param-label checkbox-label">
                    <input
                      type="checkbox"
                      className="param-checkbox"
                      checked={flightParams.optimize_angle}
                      onChange={(e) => handleParamChange('optimize_angle', e.target.checked)}
                    />
                    Optimize Angle
                  </label>
                </div>
              </div>
            </div>

            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              multiple
              accept=".kml"
              className="modal-file-input"
            />

            {/* Drop zone / File selection area */}
            <div
              className={`drop-zone ${isDark ? 'dark' : 'light'}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <div className="drop-zone-icon">📁</div>
              <p className="drop-zone-title">Drag & Drop KML files here</p>
              <p className="drop-zone-subtitle">or click to browse</p>
              <p className="drop-zone-note">(Only .kml files are supported)</p>
            </div>

            {/* Selected Files Display */}
            {selectedFiles.length > 0 && (
              <div className="selected-files">
                <p className="selected-files-title">Selected Files:</p>
                <ul className="selected-files-list">
                  {selectedFiles.map((file, index) => (
                    <li key={index} className="selected-files-item">{file.name} ({file.size} bytes)</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Upload Message */}
            {kmlUploadMessage && (
              <p className={`upload-message ${kmlUploadMessage.includes('failed') ? 'error' : 'success'}`}>
                {kmlUploadMessage}
              </p>
            )}

            {/* Modal Actions */}
            <div className="modal-actions">
              <button
                className={`modal-btn cancel ${isDark ? 'dark' : ''}`}
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFiles([]);
                  setKmlUploadMessage('');
                }}
                disabled={uploadingKML}
              >
                Cancel
              </button>
              <button
                className="modal-btn upload"
                onClick={uploadKMLFiles}
                disabled={uploadingKML || selectedFiles.length === 0}
              >
                {uploadingKML ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Drone Control Modal (formerly Drawer) */}
      {showDroneControlModal && (
        <div className="modal-overlay"> {/* Reusing modal-overlay for consistency */}
          <div className={`modal-content ${isDark ? 'dark' : 'light'}`}>
            <div className="modal-header"> {/* Reusing modal-header styles */}
              <h3 className="modal-title">Drone Control</h3>
              <button
                className="drawer-close-btn" /* Reusing drawer close button style */
                onClick={() => setShowDroneControlModal(false)}
              >
                &times;
              </button>
            </div>
            <div className="drawer-body"> {/* Reusing drawer-body for button layout */}
              <button
                className={`drawer-action-btn ${isDark ? 'dark' : 'light'}`}
                onClick={() => sendDroneCommand('arm')}
              >
                ARM 🟢
              </button>
              <button
                className={`drawer-action-btn ${isDark ? 'dark' : 'light'}`}
                onClick={() => sendDroneCommand('disarm')}
              >
                DISARM 🔴
              </button>
              <button
                className={`drawer-action-btn ${isDark ? 'dark' : 'light'}`}
                onClick={() => sendDroneCommand('rtl')}
              >
                RTL 🏠
              </button>
              <button
                className={`drawer-action-btn ${isDark ? 'dark' : 'light'}`}
                onClick={() => sendDroneCommand('land')}
              >
                LAND ⬇️
              </button>
              {/* Add more control buttons as needed */}
            </div>
            {/* Optional: Add modal actions (cancel/close) if needed for this modal */}
            <div className="modal-actions">
              <button
                className={`modal-btn cancel ${isDark ? 'dark' : ''}`}
                onClick={() => setShowDroneControlModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScoutDrone;
