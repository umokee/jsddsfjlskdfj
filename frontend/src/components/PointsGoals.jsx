import { useState, useEffect } from 'react';
import axios from 'axios';

import { API_URL } from '../config';
import { getApiKey } from '../api';

function PointsGoals({ currentPoints }) {
  const [goals, setGoals] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [showAchieved, setShowAchieved] = useState(false);
  const [formData, setFormData] = useState({
    goal_type: 'points',
    target_points: '',
    project_name: '',
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
        { headers: { 'X-API-Key': getApiKey() } }
      );
      setGoals(response.data);
    } catch (error) {
      console.error('Failed to fetch goals:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const goalData = {
      goal_type: formData.goal_type,
      reward_description: formData.reward_description,
      deadline: formData.deadline || undefined
    };

    // Add type-specific fields
    if (formData.goal_type === 'points') {
      goalData.target_points = parseInt(formData.target_points);
    } else if (formData.goal_type === 'project_completion') {
      goalData.project_name = formData.project_name;
    }

    try {
      await axios.post(`${API_URL}/api/goals`, goalData, {
        headers: { 'X-API-Key': getApiKey() }
      });
      setFormData({
        goal_type: 'points',
        target_points: '',
        project_name: '',
        reward_description: '',
        deadline: ''
      });
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
        headers: { 'X-API-Key': getApiKey() }
      });
      fetchGoals();
    } catch (error) {
      console.error('Failed to delete goal:', error);
    }
  };

  const handleClaimReward = async (goalId) => {
    try {
      await axios.post(`${API_URL}/api/goals/${goalId}/claim`, {}, {
        headers: { 'X-API-Key': getApiKey() }
      });
      fetchGoals();
    } catch (error) {
      console.error('Failed to claim reward:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to claim reward';
      alert(`Failed to claim reward: ${errorMsg}`);
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
            <label>Goal Type:</label>
            <select
              value={formData.goal_type}
              onChange={(e) => setFormData({ ...formData, goal_type: e.target.value })}
              required
            >
              <option value="points">Points Goal</option>
              <option value="project_completion">Project Completion</option>
            </select>
          </div>

          {formData.goal_type === 'points' && (
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
          )}

          {formData.goal_type === 'project_completion' && (
            <div className="form-group">
              <label>Project Name:</label>
              <input
                type="text"
                value={formData.project_name}
                onChange={(e) => setFormData({ ...formData, project_name: e.target.value })}
                required
                maxLength="200"
                placeholder="e.g., Work.Backend"
              />
            </div>
          )}

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
            const progress = goal.goal_type === 'points' ? calculateProgress(goal) : 0;
            const pointsNeeded = goal.goal_type === 'points' ? goal.target_points - (currentPoints || 0) : 0;

            return (
              <div
                key={goal.id}
                className={`goal-item ${goal.achieved ? 'achieved' : ''} ${goal.reward_claimed ? 'claimed' : ''}`}
              >
                <div className="goal-header">
                  <div className="goal-type-badge">
                    {goal.goal_type === 'points' ? 'POINTS' : 'PROJECT'}
                  </div>
                  <div className="goal-target">
                    {goal.goal_type === 'points' ? `${goal.target_points} pts` : goal.project_name}
                  </div>
                  {goal.achieved && !goal.reward_claimed && (
                    <div className="goal-badge achieved">Achieved!</div>
                  )}
                  {goal.reward_claimed && (
                    <div className="goal-badge claimed">Claimed!</div>
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

                <div className="goal-reward">Reward: {goal.reward_description}</div>

                {goal.deadline && (
                  <div className="goal-deadline">
                    Deadline: {new Date(goal.deadline).toLocaleDateString()}
                  </div>
                )}

                {!goal.achieved && goal.goal_type === 'points' && (
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

                {!goal.achieved && goal.goal_type === 'project_completion' && (
                  <div className="goal-info">
                    Complete all tasks in project "{goal.project_name}" to unlock reward
                  </div>
                )}

                {goal.achieved && goal.achieved_date && (
                  <div className="goal-achieved-date">
                    Achieved on {new Date(goal.achieved_date).toLocaleDateString()}
                  </div>
                )}

                {goal.reward_claimed && goal.reward_claimed_at && (
                  <div className="goal-claimed-date">
                    Claimed on {new Date(goal.reward_claimed_at).toLocaleDateString()}
                  </div>
                )}

                {goal.achieved && !goal.reward_claimed && (
                  <button
                    onClick={() => handleClaimReward(goal.id)}
                    className="claim-reward-btn"
                  >
                    Claim Reward
                  </button>
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
