import React, { useState } from 'react';
import { api } from '../../services/api';
import { FileText, Download, ShieldCheck, AlertOctagon, CheckCircle, BarChart2, Printer } from 'lucide-react';

export const ReportView: React.FC = () => {
  const [reportData, setReportData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerateReport = async () => {
    setIsLoading(true);
    try {
      const data = await api.generateReport();
      setReportData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!reportData) return;
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ISRO_AERIS_Flight_Report_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrintPDF = () => {
    window.print();
  };

  const summaryCards = reportData
    ? [
        {
          icon: ShieldCheck,
          label: 'Overall Health Score',
          value: `${reportData.overall_health_score}/100`,
          color: '#34d399',
          accent: 'rgba(16, 185, 129, 0.08)',
          borderColor: 'rgba(16, 185, 129, 0.2)',
          left: '#10b981',
        },
        {
          icon: CheckCircle,
          label: 'Physics Compliance',
          value: reportData.physics_compliance_score,
          color: '#22d3ee',
          accent: 'rgba(6, 182, 212, 0.08)',
          borderColor: 'rgba(6, 182, 212, 0.2)',
          left: '#06b6d4',
        },
        {
          icon: AlertOctagon,
          label: 'Critical Hazards',
          value: reportData.summary.critical_count,
          color: '#fb7185',
          accent: 'rgba(244, 63, 94, 0.08)',
          borderColor: 'rgba(244, 63, 94, 0.2)',
          left: '#f43f5e',
        },
        {
          icon: FileText,
          label: 'Total Anomalies',
          value: reportData.summary.total_anomalies,
          color: 'var(--isro-orange)',
          accent: 'rgba(249, 115, 22, 0.08)',
          borderColor: 'rgba(249, 115, 22, 0.2)',
          left: '#f97316',
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="glass-panel p-4 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div
              className="p-2 rounded-xl"
              style={{
                background: 'rgba(249, 115, 22, 0.08)',
                border: '1px solid rgba(249, 115, 22, 0.2)',
              }}
            >
              <FileText className="w-5 h-5" style={{ color: 'var(--isro-orange)' }} />
            </div>
            <h2 className="text-lg sm:text-xl font-bold tracking-wide" style={{ color: 'var(--text-main)' }}>
              Flight Analysis & Compliance Report
            </h2>
          </div>
          <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
            Generates standardized post-flight mission surveillance summaries, physics compliance audits, and anomaly catalogs.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleGenerateReport}
            disabled={isLoading}
            className="flex items-center space-x-2 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all disabled:opacity-50"
            style={{
              background: 'linear-gradient(135deg, #f97316, #f59e0b)',
              boxShadow: '0 4px 14px -2px rgba(249, 115, 22, 0.35)',
            }}
          >
            <BarChart2 className="w-4 h-4" />
            <span>{isLoading ? 'Generating...' : 'Compile Report'}</span>
          </button>

          {reportData && (
            <>
              <button
                onClick={handleDownloadJSON}
                className="flex items-center space-x-1.5 font-semibold text-xs px-3.5 py-2.5 rounded-xl transition-all"
                style={{
                  background: 'var(--pill-bg)',
                  color: 'var(--text-main)',
                  border: '1px solid var(--pill-border)',
                }}
              >
                <Download className="w-3.5 h-3.5" />
                <span>JSON Export</span>
              </button>
              <button
                onClick={handlePrintPDF}
                className="flex items-center space-x-1.5 text-white font-semibold text-xs px-3.5 py-2.5 rounded-xl transition-all"
                style={{
                  background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
                  boxShadow: '0 4px 14px -2px rgba(6, 182, 212, 0.3)',
                }}
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print / PDF</span>
              </button>
            </>
          )}
        </div>
      </div>

      {reportData && (
        <div className="space-y-6 print:text-black print:bg-white">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {summaryCards.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.label}
                  className="glass-panel p-4 flex items-center space-x-3"
                  style={{ borderLeft: `3px solid ${card.left}` }}
                >
                  <div
                    className="p-2.5 rounded-xl"
                    style={{
                      background: card.accent,
                      border: `1px solid ${card.borderColor}`,
                    }}
                  >
                    <Icon className="w-6 h-6" style={{ color: card.color }} />
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>
                      {card.label}
                    </span>
                    <p className="text-xl font-bold font-mono" style={{ color: card.color }}>
                      {card.value}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Subsystem Health */}
          <div className="glass-panel p-5 space-y-3">
            <h3
              className="text-sm font-bold pb-2.5 uppercase tracking-wider"
              style={{ color: 'var(--text-main)', borderBottom: '1px solid var(--divider)' }}
            >
              Subsystem Operational Status
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              {Object.entries(reportData.subsystem_health || {}).map(([subsys, status]) => (
                <div
                  key={subsys}
                  className="p-3.5 rounded-xl flex justify-between items-center"
                  style={{
                    background: 'var(--pill-bg)',
                    border: '1px solid var(--pill-border)',
                  }}
                >
                  <span className="font-semibold" style={{ color: 'var(--text-sub)' }}>
                    {subsys}
                  </span>
                  <span
                    className="px-2 py-0.5 rounded-lg font-mono font-bold text-[10px]"
                    style={{
                      background: status === 'NOMINAL' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                      color: status === 'NOMINAL' ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                      border: `1px solid ${status === 'NOMINAL' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)'}`,
                    }}
                  >
                    {String(status)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Anomaly Catalog Table */}
          <div className="glass-panel p-5 space-y-3">
            <h3
              className="text-sm font-bold pb-2.5 uppercase tracking-wider"
              style={{ color: 'var(--text-main)', borderBottom: '1px solid var(--divider)' }}
            >
              Anomaly Catalog ({reportData.anomalies_catalog.length})
            </h3>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time (T+)</th>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.anomalies_catalog.map((a: any, idx: number) => (
                    <tr key={idx}>
                      <td className="font-mono font-bold" style={{ color: 'var(--isro-orange)' }}>
                        T+{a.timestamp.toFixed(1)}s
                      </td>
                      <td className="font-semibold" style={{ color: 'var(--text-main)' }}>
                        {a.parameter}
                      </td>
                      <td style={{ color: 'var(--accent-cyan)' }}>{a.anomaly_type}</td>
                      <td>
                        <span
                          className="px-2.5 py-0.5 rounded-lg text-[10px] font-bold font-mono"
                          style={{
                            background: a.severity === 'CRITICAL' ? 'rgba(244, 63, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                            color: a.severity === 'CRITICAL' ? '#fb7185' : '#fbbf24',
                            border: `1px solid ${a.severity === 'CRITICAL' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)'}`,
                          }}
                        >
                          {a.severity}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{a.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
