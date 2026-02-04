/**
 * Points goals component.
 */
import { useState, useEffect } from 'react';
import { useGoals } from '../hooks/useGoals';

function PointsGoals({ currentPoints }) {
  const { goals, loadGoals, createGoal, deleteGoal, claimReward } = useGoals();
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
    loadGoals(showAchieved);
  }, [showAchieved, loadGoals]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const goalData = {
      goal_type: formData.goal_type,
      reward_description: formData.reward_description,
      deadline: formData.deadline || undefined
    };

    if (formData.goal_type === 'points') {
      goalData.target_points = parseInt(formData.target_points);
    } else if (formData.goal_type === 'project_completion') {
      goalData.project_name = formData.project_name;
    }

    try {
      await createGoal(goalData);
      setFormData({
        goal_type: 'points',
        target_points: '',
        project_name: '',
        reward_description: '',
        deadline: ''
      });
      setShowForm(false);
      loadGoals(showAchieved);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to create goal';
      alert(`Failed to create goal: ${errorMsg}`);
    }
  };

  const handleDelete = async (goalId) => {
    if (!confirm('Delete this goal?')) return;

    try {
      await deleteGoal(goalId);
      loadGoals(showAchieved);
    } catch (error) {
      console.error('Failed to delete goal:', error);
    }
  };

  const handleClaimReward = async (goalId) => {
    try {
      await claimReward(goalId);
      loadGoals(showAchieved);
    } catch (error) {
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
                      x
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

                {!goal.achieved && goal.goal_type === 'project_completion' && goal.total_tasks !== undefined && (
                  <>
                    <div className="goal-progress">
                      <div
                        className="goal-progress-bar"
                        style={{ width: `${goal.total_tasks > 0 ? (goal.completed_tasks / goal.total_tasks * 100) : 0}%` }}
                      ></div>
                    </div>
                    <div className="goal-stats">
                      <span>{goal.completed_tasks} / {goal.total_tasks} tasks</span>
                      <span>
                        {goal.total_tasks > 0
                          ? `${goal.total_tasks - goal.completed_tasks} tasks to go`
                          : 'No tasks in project'}
                      </span>
                    </div>
                  </>
                )}

                {goal.achieved && goal.achieved_date && (
                  <div className="goal-achieved-date">
                    Achieved on {new Date(goal.achieved_date).toLocaleDateString()}
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
