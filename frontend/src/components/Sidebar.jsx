import { useState } from 'react';

function Sidebar({ currentView, onViewChange }) {
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { id: 'tasks', label: 'Tasks', icon: '☐' },
    { id: 'points', label: 'Points', icon: '★' },
    { id: 'goals', label: 'Goals', icon: '🎯' },
    { id: 'calculator', label: 'Calculator', icon: '📊' },
    { id: 'settings', label: 'Settings', icon: '⚙' },
  ];

  return (
    <>
      <button
        className="sidebar-toggle"
        onClick={() => setCollapsed(!collapsed)}
        aria-label="Toggle sidebar"
      >
        ☰
      </button>

      <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <h1 className="sidebar-logo">{collapsed ? 'TM' : 'TASK MANAGER'}</h1>
        </div>

        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <button
              key={item.id}
              className={`sidebar-item ${currentView === item.id ? 'active' : ''}`}
              onClick={() => onViewChange(item.id)}
              title={collapsed ? item.label : ''}
            >
              <span className="sidebar-icon">{item.icon}</span>
              {!collapsed && <span className="sidebar-label">{item.label}</span>}
            </button>
          ))}
        </nav>
      </aside>
    </>
  );
}

export default Sidebar;
