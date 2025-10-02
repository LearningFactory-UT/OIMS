// src/components/TopBar.jsx
import React, { useState, useEffect } from "react";
import io from "socket.io-client";

let socket;

function TopBar({ onSettingsClick }) {
    const [currentTime, setCurrentTime] = useState("");
    const [remainingTime, setRemainingTime] = useState(0);
    const [timerRunning, setTimerRunning] = useState(false);

    useEffect(() => {
        socket = io("http://rtlsserver.local:3010");
        socket.on("timer_start", (data) => {
            setRemainingTime(data.duration);
            setTimerRunning(true);
        });
        socket.on("timer_pause", (data) => {
            setTimerRunning(false);
            setRemainingTime(data.paused_time);
        });
        socket.on("timer_resume", (data) => {
            setRemainingTime(data.remaining);
            setTimerRunning(true);
        });
        socket.on("timer_stop", () => {
            setTimerRunning(false);
            setRemainingTime(0);
        });
        socket.on("timer_ended", () => {
            setTimerRunning(false);
            setRemainingTime(0);
        });

        return () => {
            socket.disconnect();
        };
    }, []);

    useEffect(() => {
        let intervalId;
        if (timerRunning) {
            intervalId = setInterval(() => {
                setRemainingTime((prev) => (prev <= 1 ? 0 : prev - 1));
            }, 1000);
        }
        return () => clearInterval(intervalId);
    }, [timerRunning]);

    useEffect(() => {
        const clockInterval = setInterval(() => {
            const now = new Date();
            const hh = String(now.getHours()).padStart(2, "0");
            const mm = String(now.getMinutes()).padStart(2, "0");
            const ss = String(now.getSeconds()).padStart(2, "0");
            setCurrentTime(`${hh}:${mm}:${ss}`);
        }, 1000);
        return () => clearInterval(clockInterval);
    }, []);

    const formatRemaining = (seconds) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    };

    return (
        <div className="top-bar">
            <img src="/logo.png" alt="Logo" />
            <div className="title">Inventory</div>

            <div className="time">{currentTime}</div>
            <div className="timer">Remaining: {formatRemaining(remainingTime)}</div>

            {/* 
                Instead of setShowSettingsModal(true),
                we just call a callback given by the parent.
            */}
            <button className="settings-button" onClick={onSettingsClick}>
                Settings
            </button>
        </div>
    );
}

export default TopBar;