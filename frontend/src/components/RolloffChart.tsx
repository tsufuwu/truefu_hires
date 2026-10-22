// components/RolloffChart.tsx — Interactive 95th-pct spectral roll-off curve with i18n
import { useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend,
  type ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { RolloffCurveData } from '../api';
import type { translations } from '../i18n';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend);

interface Props {
  data: RolloffCurveData;
  detectedCutoffHz?: number | null;
  t: typeof translations['en']['visuals'];
}

export function RolloffChart({ data, detectedCutoffHz, t }: Props) {
  const chartRef = useRef<ChartJS<'line'>>(null);

  // Downsample for readability (max 200 points)
  const step = Math.max(1, Math.floor(data.frequencies_khz.length / 200));
  const labels = data.frequencies_khz.filter((_, i) => i % step === 0).map(f => f.toFixed(1));
  const values = data.energy_dbfs.filter((_, i) => i % step === 0);

  const cutoffLabel = detectedCutoffHz ? `${(detectedCutoffHz / 1000).toFixed(2)} kHz` : null;

  const chartData = {
    labels,
    datasets: [
      {
        label: `${t.energyAxis} (dBFS)`,
        data: values,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.08)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: '#00e5ff',
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 800 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#111724',
        borderColor: 'rgba(99,130,201,0.3)',
        borderWidth: 1,
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        callbacks: {
          title: ([item]) => `${item.label} kHz`,
          label: (item) => `${(item.raw as number).toFixed(1)} dBFS`,
        },
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255,255,255,0.04)' },
        ticks: {
          color: '#64748b',
          maxTicksLimit: 12,
          callback: (_val, i) => i % 20 === 0 ? labels[i] : '',
          font: { family: 'JetBrains Mono', size: 10 },
        },
        title: { display: true, text: t.freqAxis, color: '#64748b', font: { size: 11, weight: 'bold' } },
      },
      y: {
        grid: { color: 'rgba(255,255,255,0.04)' },
        ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } },
        title: { display: true, text: t.energyAxis, color: '#64748b', font: { size: 11, weight: 'bold' } },
        min: -130,
        max: 10,
      },
    },
  };

  // Draw cutoff line as a plugin
  const cutoffPlugin = {
    id: 'cutoff-line',
    afterDraw(chart: ChartJS) {
      if (!detectedCutoffHz) return;
      const { ctx, scales } = chart;
      const xScale = scales.x;
      if (!xScale) return;
      const cutoffKhz = detectedCutoffHz / 1000;
      const idx = labels.findIndex(l => parseFloat(l) >= cutoffKhz);
      if (idx < 0) return;
      const x = xScale.getPixelForValue(idx);
      const yTop = chart.chartArea.top;
      const yBot = chart.chartArea.bottom;

      ctx.save();
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.85;
      ctx.beginPath();
      ctx.moveTo(x, yTop);
      ctx.lineTo(x, yBot);
      ctx.stroke();

      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 11px Inter, sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(`⬤ ${t.cutoffBadge} ${cutoffKhz.toFixed(2)} kHz`, x + 6, yTop + 16);
      ctx.restore();
    },
  };

  return (
    <div className="card p-5 fade-in" id="rolloff-chart-card">
      <h3 className="text-sm font-bold mb-4 text-slate-200">
        {t.rolloffTitle}
        {cutoffLabel && (
          <span className="ml-3 text-xs font-semibold px-2 py-0.5 rounded-full mono"
            style={{ background: 'rgba(0,229,255,0.12)', color: 'var(--accent-cyan)', border: '1px solid rgba(0,229,255,0.35)' }}>
            {t.cutoffBadge}: {cutoffLabel}
          </span>
        )}
      </h3>
      <div style={{ height: '260px' }}>
        <Line
          ref={chartRef}
          data={chartData}
          options={options}
          plugins={[cutoffPlugin as any]}
        />
      </div>
    </div>
  );
}
