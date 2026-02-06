import { useState } from 'react';
import { pointsApi } from '../../../shared/api';

function PointsCalculator() {
  const [targetDate, setTargetDate] = useState('');
  const [projection, setProjection] = useState(null);
  const [calculating, setCalculating] = useState(false);

  const handleCalculate = async () => {
    if (!targetDate) {
      alert('Please select a target date');
      return;
    }

    setCalculating(true);
    try {
      const response = await pointsApi.getProjection(targetDate);
      setProjection(response.data);
    } catch (error) {
      console.error('Failed to calculate projection:', error);
      alert('Failed to calculate projection');
    } finally {
      setCalculating(false);
    }
  };

  return (
    <div className="points-calculator">
      <h2>Points Calculator</h2>
      <p>Calculate how many points you can earn by a target date</p>

      <div className="calculator-input">
        <label>Target Date:</label>
        <input
          type="date"
          value={targetDate}
          onChange={(e) => setTargetDate(e.target.value)}
          min={new Date().toISOString().split('T')[0]}
        />
        <button onClick={handleCalculate} disabled={calculating}>
          {calculating ? 'Calculating...' : 'Calculate'}
        </button>
      </div>

      {projection && (
        <div className="projection-results">
          <div className="projection-header">
            <h3>Projection for {new Date(targetDate).toLocaleDateString()}</h3>
            <p>{projection.days_until} days from now</p>
          </div>

          <div className="projection-stats">
            <div className="stat-card">
              <div className="stat-label">Current Total</div>
              <div className="stat-value">{projection.current_total}</div>
            </div>

            <div className="stat-card">
              <div className="stat-label">Avg Per Day (Last 30)</div>
              <div className="stat-value">{projection.avg_per_day}</div>
            </div>
          </div>

          <div className="projection-ranges">
            <h4>Projected Totals:</h4>

            <div className="range-item pessimistic">
              <div className="range-label">
                Minimum (70% of average)
              </div>
              <div className="range-value">{projection.min_projection}</div>
              <div className="range-diff">
                +{projection.min_projection - projection.current_total} from now
              </div>
            </div>

            <div className="range-item realistic">
              <div className="range-label">
                Most Likely (current average)
              </div>
              <div className="range-value">{projection.avg_projection}</div>
              <div className="range-diff">
                +{projection.avg_projection - projection.current_total} from now
              </div>
            </div>

            <div className="range-item optimistic">
              <div className="range-label">
                Maximum (130% of average)
              </div>
              <div className="range-value">{projection.max_projection}</div>
              <div className="range-diff">
                +{projection.max_projection - projection.current_total} from now
              </div>
            </div>
          </div>

          <div className="projection-note">
            Projections are based on your last 30 days performance.
            Actual results may vary based on your daily completion rate.
          </div>
        </div>
      )}
    </div>
  );
}

export default PointsCalculator;
