import { useState, useEffect } from 'react';
import axios from 'axios';

import { API_URL } from '../config';
import { getApiKey } from '../api';

function PointsDisplay() {
  const [currentPoints, setCurrentPoints] = useState(0);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [days, setDays] = useState(7);

  useEffect(() => {
    fetchCurrentPoints();
    fetchHistory();
  }, [days]);

  const fetchCurrentPoints = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/points/current`, {
        headers: { 'X-API-Key': getApiKey() }
      });
      setCurrentPoints(response.data.points);
    } catch (error) {
      console.error('Failed to fetch current points:', error);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/points/history?days=${days}`, {
        headers: { 'X-API-Key': getApiKey() }
      });
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch points history:', error);
    }
  };

  const getTodayStats = () => {
    if (history.length === 0) return null;
    return history[0]; // Most recent (today)
  };

  const todayStats = getTodayStats();

  return (
    <div className="points-display">
      <div className="points-current">
        <h2>Total Points</h2>
        <div className="points-value">{currentPoints}</div>
        {todayStats && (
          <div className="points-today">
            <div>Today: {todayStats.daily_total > 0 ? '+' : ''}{todayStats.daily_total}</div>
            <div className="points-breakdown">
              <span className="earned">+{todayStats.points_earned}</span>
              {todayStats.points_penalty > 0 && (
                <span className="penalty">-{todayStats.points_penalty}</span>
              )}
            </div>
          </div>
        )}
      </div>

      <button
        className="toggle-history-btn"
        onClick={() => setShowHistory(!showHistory)}
      >
        {showHistory ? 'Hide History' : 'Show History'}
      </button>

      {showHistory && (
        <div className="points-history">
          <div className="history-controls">
            <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
            </select>
          </div>

          <div className="history-list">
            {history.map((entry) => (
              <div key={entry.id} className="history-entry">
                <div className="history-date">
                  {new Date(entry.date).toLocaleDateString()}
                </div>
                <div className="history-stats">
                  <div className="stat">
                    <span className="stat-label">Tasks:</span>
                    <span className="stat-value">{entry.tasks_completed}/{entry.tasks_planned}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Habits:</span>
                    <span className="stat-value">{entry.habits_completed}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Rate:</span>
                    <span className="stat-value">{(entry.completion_rate * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div className="history-points">
                  <div className="earned">+{entry.points_earned}</div>
                  {entry.points_penalty > 0 && (
                    <div className="penalty">-{entry.points_penalty}</div>
                  )}
                  <div className={`total ${entry.daily_total < 0 ? 'negative' : ''}`}>
                    {entry.daily_total > 0 ? '+' : ''}{entry.daily_total}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default PointsDisplay;
