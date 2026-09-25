import React from 'react';
import { Grid } from 'lucide-react';

interface CorrelationHeatmapProps {
  matrix: Record<string, Record<string, number>>;
}

export const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({ matrix }) => {
  const keys = Object.keys(matrix);

  const getHeatmapStyle = (val: number) => {
    if (val > 0.7) return { background: 'rgba(249, 115, 22, 0.45)', color: 'var(--text-main)', fontWeight: 700 };
    if (val > 0.4) return { background: 'rgba(245, 158, 11, 0.3)', color: 'var(--text-main)', fontWeight: 600 };
    if (val < -0.4) return { background: 'rgba(6, 182, 212, 0.35)', color: 'var(--text-main)', fontWeight: 600 };
    return { background: 'var(--pill-bg)', color: 'var(--text-muted)', fontWeight: 400 };
  };

  return (
    <div className="glass-panel p-3 sm:p-5 flex flex-col h-[320px]">
      {/* Header */}
      <div
        className="flex items-center space-x-2.5 mb-3 pb-2.5"
        style={{ borderBottom: '1px solid var(--divider)' }}
      >
        <div
          className="p-2 rounded-xl"
          style={{
            background: 'rgba(249, 115, 22, 0.08)',
            border: '1px solid rgba(249, 115, 22, 0.2)',
          }}
        >
          <Grid className="w-4 h-4" style={{ color: 'var(--isro-orange)' }} />
        </div>
        <h2 className="text-xs sm:text-sm font-bold tracking-wide uppercase" style={{ color: 'var(--text-main)' }}>
          Physics Correlation Matrix
        </h2>
      </div>

      {keys.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-xs" style={{ color: 'var(--text-muted)' }}>
          Loading correlation matrix...
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto overflow-y-auto">
          <table className="w-full text-center border-collapse">
            <thead>
              <tr>
                <th
                  className="p-1 sm:p-1.5 text-[9px] sm:text-[10px] font-mono text-left font-semibold"
                  style={{ color: 'var(--text-muted)' }}
                >
                  PARAM
                </th>
                {keys.map((k) => (
                  <th
                    key={k}
                    className="p-1 sm:p-1.5 text-[9px] sm:text-[10px] font-mono font-semibold"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {k.substring(0, 6)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keys.map((rowKey) => (
                <tr key={rowKey}>
                  <td
                    className="p-1 sm:p-1.5 text-[9px] sm:text-[10px] font-mono text-left font-semibold whitespace-nowrap"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {rowKey}
                  </td>
                  {keys.map((colKey) => {
                    const val = matrix[rowKey]?.[colKey] ?? 0;
                    const cellStyle = getHeatmapStyle(val);
                    return (
                      <td
                        key={colKey}
                        className="p-1 sm:p-1.5 text-[9px] sm:text-[11px] font-mono rounded-md m-0.5 transition-all"
                        style={cellStyle}
                        title={`${rowKey} ↔ ${colKey}: ${val.toFixed(3)}`}
                      >
                        {val.toFixed(2)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
