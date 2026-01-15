import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY;

function PointsGoals({ currentPoints }) {
  const [goals, setGoals] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [showAchieved, setShowAchieved] = useState(false);
  const [formData, setFormData] = useState({
    target_points: '',
    reward_description: '',
    deadline: ''
  });

  useEffect(() => {
    fetchGoals();
  }, [showAchieved]);

  const fetchGoals = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/api/goals?include_achieved=${showAchieved}`,
        { headers: { 'X-API-Key': API_KEY } }
      );
      setGoals(response.data);
    } catch (error) {
      console.error('Failed to fetch goals:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const goalData = {
      target_points: parseInt(formData.target_points),
      reward_description: formData.reward_description,
      deadline: formData.deadline || undefined  // Send undefined so it's omitted from JSON
    };

    try {
      await axios.post(`${API_URL}/api/goals`, goalData, {
        headers: { 'X-API-Key': API_KEY }
      });
      setFormData({ target_points: '', reward_description: '', deadline: '' });
      setShowForm(false);
      fetchGoals();
    } catch (error) {
      console.error('Failed to create goal:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to create goal';
      alert(`Failed to create goal: ${errorMsg}`);
    }
  };

  const handleDelete = async (goalId) => {
    if (!confirm('Delete this goal?')) return;

    try {
      await axios.delete(`${API_URL}/api/goals/${goalId}`, {
        headers: { 'X-API-Key': API_KEY }
      });
      fetchGoals();
    } catch (error) {
      console.error('Failed to delete goal:', error);
    }
  };

  const calculateProgress = (goal) => {
    if (!currentPoints) return 0;
    return Math.min((currentPoints / goal.target_points) * 100, 100);
  };

  return (
    <div className="points-goals">
      <div className="goals-header">
        <h2>Goals</h2>
        <div className="goals-controls">
          <button onClick={() => setShowAchieved(!showAchieved)}>
            {showAchieved ? 'Hide Achieved' : 'Show Achieved'}
          </button>
          <button onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : 'New Goal'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="goal-form">
          <div className="form-group">
            <label>Target Points:</label>
            <input
              type="number"
              value={formData.target_points}
              onChange={(e) => setFormData({ ...formData, target_points: e.target.value })}
              required
              min="1"
            />
          </div>
          <div className="form-group">
            <label>Reward Description:</label>
            <input
              type="text"
              value={formData.reward_description}
              onChange={(e) => setFormData({ ...formData, reward_description: e.target.value })}
              required
              maxLength="500"
              placeholder="What will you do when you reach this goal?"
            />
          </div>
          <div className="form-group">
            <label>Deadline (optional):</label>
            <input
              type="date"
              value={formData.deadline}
              onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
            />
          </div>
          <button type="submit">Create Goal</button>
        </form>
      )}

      <div className="goals-list">
        {goals.length === 0 ? (
          <div className="no-goals">
            {showAchieved ? 'No achieved goals yet' : 'No active goals. Create one!'}
          </div>
        ) : (
          goals.map((goal) => {
            const progress = calculateProgress(goal);
            const pointsNeeded = goal.target_points - (currentPoints || 0);

            return (
              <div
                key={goal.id}
                className={`goal-item ${goal.achieved ? 'achieved' : ''}`}
              >
                <div className="goal-header">
                  <div className="goal-target">{goal.target_points} pts</div>
                  {goal.achieved && (
                    <div className="goal-badge">Achieved!</div>
                  )}
                  {!goal.achieved && (
                    <button
                      onClick={() => handleDelete(goal.id)}
                      className="delete-btn"
                    >
                      ×
                    </button>
                  )}
                </div>

                <div className="goal-reward">{goal.reward_description}</div>

                {goal.deadline && (
                  <div className="goal-deadline">
                    Deadline: {new Date(goal.deadline).toLocaleDateString()}
                  </div>
                )}

                {!goal.achieved && (
                  <>
                    <div className="goal-progress">
                      <div
                        className="goal-progress-bar"
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                    <div className="goal-stats">
                      <span>{progress.toFixed(0)}% complete</span>
                      <span>{pointsNeeded > 0 ? `${pointsNeeded} points to go` : 'Goal reached!'}</span>
                    </div>
                  </>
                )}

                {goal.achieved && goal.achieved_date && (
                  <div className="goal-achieved-date">
                    Achieved on {new Date(goal.achieved_date).toLocaleDateString()}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default PointsGoals;
