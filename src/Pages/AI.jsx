import React, { useEffect, useState, useRef } from 'react';
import '../assets/CSS/AI.css';

const AI = () => {
  const [isDark, setIsDark] = useState(false);
  const [activePane, setActivePane] = useState('crops');
  const [terminalOutput, setTerminalOutput] = useState('Ready to process AI detection...');
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
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
      setTerminalOutput(prev => prev + '\n❌ Error loading AI images. Please check connection.');
    }
  };

  const runAIScript = async () => {
    setLoading(true);
    setTerminalOutput(prev => prev + '\n🚀 Initializing AI processing...\n');
    
    try {
      const response = await fetch('http://127.0.0.1:9080/run-ai-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setTerminalOutput(prev => prev + '\n✅ AI processing completed successfully!\n' + result.output);
        // Refresh images after processing
        setTimeout(() => {
          fetchAIImages();
        }, 2000);
      } else {
        setTerminalOutput(prev => prev + '\n❌ AI processing failed: ' + result.message);
      }
    } catch (error) {
      setTerminalOutput(prev => prev + '\n❌ Error running AI script: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const reloadAIData = async () => {
    setTerminalOutput(prev => prev + '\n🔄 Reloading AI data...');
    try {
      const response = await fetch('http://127.0.0.1:9080/reload-ai-data', {
        method: 'POST'
      });
      const result = await response.json();
      setTerminalOutput(prev => prev + '\n✅ AI data reloaded successfully');
      fetchAIImages();
    } catch (error) {
      setTerminalOutput(prev => prev + '\n❌ Error reloading data: ' + error.message);
    }
  };

  const fetchImageInfo = async (imageName, overlayRef) => {
    if (overlayRef.dataset.loaded === "true") return;

    try {
      const response = await fetch(`http://127.0.0.1:9080/get-image-info/${imageName}`);
      const data = await response.json();
      
      overlayRef.dataset.loaded = "true";
      overlayRef.innerHTML = Object.keys(data).length === 0
        ? '<div class="no-data">No detection data available</div>'
        : Object.entries(data)
            .filter(([key]) => key !== 'crop_path') // Hide internal paths
            .map(([key, value]) => {
              const displayKey = key.replace(/_/g, ' ').toUpperCase();
              return `<div class="info-row"><span class="key">${displayKey}:</span> <span class="value">${value}</span></div>`;
            })
            .join('');
    } catch (error) {
      overlayRef.innerHTML = '<div class="error">Failed to load detection info</div>';
    }
  };

  // Map control functions
  const handleShowAll = () => {
    setTerminalOutput(prev => prev + '\n📍 Showing all detections on map...');
    // Send message to iframe to show all markers
    if (mapFrameRef.current) {
      mapFrameRef.current.contentWindow.postMessage({
        action: 'showAll'
      }, '*');
    }
  };

  const handleCenterView = () => {
    setTerminalOutput(prev => prev + '\n🎯 Centering map view...');
    // Send message to iframe to center the view
    if (mapFrameRef.current) {
      mapFrameRef.current.contentWindow.postMessage({
        action: 'centerView'
      }, '*');
    }
  };

  useEffect(() => {
    if (isDark) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }
  }, [isDark]);

  return (
    <div className={`ai-page ${isDark ? 'dark-mode' : ''}`}>
      <div className="header">
        <div className="logo-section">
          <div className="logo-placeholder">AI</div>
          <h1 className="heading">Object Detection Studio</h1>
        </div>
        
        <div className="control-section">
          <div className="action-buttons">
            <button 
              className={`action-btn primary ${loading ? 'loading' : ''}`}
              onClick={runAIScript}
              disabled={loading}
            >
              {loading ? '⏳ Processing...' : '🚀 Run Detection'}
            </button>
            
            <button 
              className="action-btn secondary"
              onClick={reloadAIData}
            >
              🔄 Refresh Data
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
    </div>
  );
};

export default AI;