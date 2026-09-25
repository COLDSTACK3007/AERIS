import React from 'react';
import { LayoutDashboard, Activity, AlertTriangle, Layers, FileText, Award, TrendingUp } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
    { id: 'telemetry', label: 'Telemetry Stream', icon: Activity },
    { id: 'anomalies', label: 'Anomaly Engine', icon: AlertTriangle },
    { id: 'imputation', label: 'Physics & Recovery', icon: Layers },
    { id: 'prediction', label: 'Drift Prediction', icon: TrendingUp },
    { id: 'evaluation', label: 'Evaluation Report', icon: Award },
    { id: 'reports', label: 'Flight Reports', icon: FileText },
  ];

  return (
    <aside
      className="w-full lg:w-64 glass-panel p-2.5 sm:p-4 flex flex-row lg:flex-col justify-between items-center lg:items-stretch gap-2 lg:gap-0 lg:sticky lg:top-6 lg:self-start flex-shrink-0 z-20 overflow-hidden select-none"
      style={{ transform: 'none', overflow: 'hidden' }}
    >
      <div className="flex flex-row lg:flex-col space-x-1.5 lg:space-x-0 lg:space-y-1.5 w-full overflow-hidden">
        <div
          className="hidden lg:block text-[10px] font-bold uppercase px-3 mb-3 tracking-widest font-mono select-none"
          style={{ color: 'var(--text-muted)' }}
        >
          SYSTEM MODULES
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex-1 lg:w-full flex items-center justify-center lg:justify-start space-x-2 lg:space-x-3 px-3 py-2.5 lg:px-3.5 lg:py-3 rounded-xl text-xs font-bold transition-all duration-300 ease-in-out relative whitespace-nowrap select-none group ${
                isActive ? 'shadow-sm scale-[1.01]' : 'hover:bg-[var(--pill-bg)]'
              }`}
              style={{
                background: isActive ? 'var(--isro-orange-glow)' : 'transparent',
                color: isActive ? 'var(--isro-orange)' : 'var(--text-muted)',
                border: isActive
                  ? '1px solid var(--isro-orange-border)'
                  : '1px solid transparent',
              }}
            >
              {isActive && (
                <div
                  className="hidden lg:block absolute left-0 top-2 bottom-2 w-1 rounded-r-full shadow-sm"
                  style={{
                    background: 'var(--isro-orange)',
                    boxShadow: '0 0 8px var(--isro-orange)',
                  }}
                />
              )}
              <Icon
                className="w-4 h-4 flex-shrink-0 transition-colors"
                style={{ color: isActive ? 'var(--isro-orange)' : 'var(--text-muted)' }}
              />
              <span
                className="tracking-wide text-[11px] sm:text-xs transition-colors"
                style={{ color: isActive ? 'var(--isro-orange)' : 'var(--text-main)' }}
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Bottom Status Card (Desktop Only) */}
      <div
        className="hidden lg:block p-3.5 rounded-xl text-xs space-y-2.5 mt-auto"
        style={{
          background: 'var(--pill-bg)',
          border: '1px solid var(--pill-border)',
        }}
      >
        <div className="flex items-center justify-between">
          <span
            className="font-bold font-mono text-[11px] tracking-wider"
            style={{ color: 'var(--text-main)' }}
          >
            ISRO TELEMETRY
          </span>
          <span
            className="text-[10px] px-2 py-0.5 rounded-md font-mono font-bold"
            style={{
              background: 'rgba(16, 185, 129, 0.12)',
              color: 'var(--accent-emerald)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
            }}
          >
            ONLINE
          </span>
        </div>
        <div
          className="flex items-center space-x-2 text-[11px] font-mono font-semibold"
          style={{ color: 'var(--accent-emerald)' }}
        >
          <span
            className="w-2 h-2 rounded-full animate-pulse-glow"
            style={{ background: 'var(--accent-emerald)' }}
          />
          <span>16 Channels Active</span>
        </div>
      </div>
    </aside>
  );
};
