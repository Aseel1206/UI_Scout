// RosSidebar.js
import React, { useEffect, useState } from 'react';
import ROSLIB from 'roslib';
import './Layout.css'; // same CSS from earlier

const RosSidebar = ({ open, setOpen }) => {
  const [battery, setBattery] = useState(null);
  const [mode, setMode] = useState(null);
  const [rosConnected, setRosConnected] = useState(false);

  useEffect(() => {
    const ros = new ROSLIB.Ros({
      url: 'ws://localhost:9090' // Adjust if running remotely
    });

    ros.on('connection', () => {
      setRosConnected(true);
      console.log('Connected to ROS!');
    });

    ros.on('error', (error) => {
      console.error('ROS connection error:', error);
    });

    ros.on('close', () => {
      setRosConnected(false);
      console.log('Connection to ROS closed.');
    });

    const batteryListener = new ROSLIB.Topic({
      ros,
      name: '/mavros/battery',
      messageType: 'sensor_msgs/BatteryState'
    });

    const stateListener = new ROSLIB.Topic({
      ros,
      name: '/mavros/state',
      messageType: 'mavros_msgs/State'
    });

    batteryListener.subscribe((message) => {
      setBattery(message.percentage);
    });

    stateListener.subscribe((message) => {
      setMode(message.mode);
    });

    return () => {
      batteryListener.unsubscribe();
      stateListener.unsubscribe();
      ros.close();
    };
  }, []);

  return (
    <div className={`sidebar ${open ? 'open' : ''}`}>
      <button className='close-btn' onClick={() => setOpen(false)}>×</button>
      <h2>ROS Status</h2>
      <p><strong>ROS:</strong> {rosConnected ? '🟢 Connected' : '🔴 Disconnected'}</p>
      <p><strong>Flight Mode:</strong> {mode || '---'}</p>
      <p><strong>Battery:</strong> {battery != null ? (battery * 100).toFixed(1) + '%' : '---'}</p>
      <nav>
        <ul>
          <li><a href="/">Home</a></li>
          <li><a href="/manual">Manual</a></li>
          <li><a href="/ai">AI</a></li>
          <li><a href="/camera">Camera</a></li>
        </ul>
      </nav>
    </div>
  );
};

export default RosSidebar;
