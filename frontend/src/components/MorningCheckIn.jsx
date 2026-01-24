import { useState } from 'react';
import axios from 'axios';
import { API_URL } from '../config';
import { getApiKey } from '../api';

const MorningCheckIn = ({ onComplete }) => {
  const [selectedMood, setSelectedMood] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const moodLevels = [
    { value: 0, label: 'EXHAUSTED', description: 'Barely functional, minimal tasks only' },
    { value: 1, label: 'TIRED', description: 'Low energy, simple tasks preferred' },
    { value: 2, label: 'OKAY', description: 'Average energy, moderate tasks' },
    { value: 3, label: 'GOOD', description: 'Solid energy, ready for work' },
    { value: 4, label: 'STRONG', description: 'High energy, tackle challenging tasks' },
    { value: 5, label: 'PEAK', description: 'Maximum energy, bring on the hardest tasks!' },
  ];

  const handleSubmit = async () => {
    if (selectedMood === null) {
      setError('Please select your energy level');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const apiKey = getApiKey();
      const response = await axios.post(
        `${API_URL}/api/tasks/complete-roll`,
        null,
        {
          params: { mood: selectedMood },
          headers: { 'X-API-Key': apiKey },
        }
      );

      if (onComplete) {
        onComplete(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to complete morning check-in');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" style={{ zIndex: 9999 }}>
      <div className="modal-content morning-checkin-modal">
        <div className="modal-header">
          <h3>⚡ MORNING CHECK-IN</h3>
        </div>

        <div className="modal-body">
          <div className="morning-checkin-intro">
            <p>SELECT YOUR ENERGY LEVEL FOR TODAY</p>
            <small>This will determine which tasks are scheduled for you</small>
          </div>

          {error && (
            <div className="error-message" style={{ marginTop: '1rem' }}>
              {error}
            </div>
          )}

          <div className="mood-selector">
            {moodLevels.map((mood) => (
              <button
                key={mood.value}
                className={`mood-option ${selectedMood === mood.value ? 'selected' : ''}`}
                onClick={() => setSelectedMood(mood.value)}
                disabled={isSubmitting}
              >
                <div className="mood-header">
                  <span className="mood-value">E{mood.value}</span>
                  <span className="mood-label">{mood.label}</span>
                </div>
                <div className="mood-description">{mood.description}</div>
              </button>
            ))}
          </div>

          <button
            className="btn btn-primary btn-block"
            onClick={handleSubmit}
            disabled={selectedMood === null || isSubmitting}
            style={{ marginTop: '1.5rem' }}
          >
            {isSubmitting ? 'PROCESSING...' : 'CONFIRM & START DAY'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MorningCheckIn;
