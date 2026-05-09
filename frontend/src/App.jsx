import { useMetrics } from './hooks/useMetrics';
import MetricChart from './components/MetricChart';

function App() {
  console.log("App is rendering")
  const { metrics, status, error } = useMetrics(30, 2000);

  return (
    <div className="min-h-screen bg-black text-gray-100 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 pb-6 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">PEACE SYSTEM</h1>
          <p className="text-gray-500 text-sm font-mono">Observability Dashboard v1.0</p>
        </div>
        
        <div className="flex gap-6">
          <div className="text-right">
            <p className="text-xs text-gray-500 uppercase font-mono">DB Events</p>
            <p className="text-xl font-semibold text-emerald-500">{status.total_events.toLocaleString()}</p>
          </div>
          <div className="text-right border-l border-gray-800 pl-6">
            <p className="text-xs text-gray-500 uppercase font-mono">API Status</p>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${status.status === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
              <p className="text-xl font-semibold uppercase">{status.status}</p>
            </div>
          </div>
        </div>
      </header>

      <main>
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-900/50 text-red-400 rounded-lg font-mono text-sm">
            critical_error: {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MetricChart 
            title="CPU USAGE (%)" 
            data={metrics} 
            dataKey="cpu"
            color="#10B981" 
          />
          <MetricChart 
            title="RAM USAGE (%)" 
            data={metrics} 
            dataKey="ram"
            color="#3B82F6" 
          />
        </div>

        <section className="mt-8 bg-gray-900/50 border border-gray-800 rounded-xl p-6">
          <h2 className="text-gray-400 text-sm font-mono uppercase mb-4">Recent System Events</h2>
          <div className="space-y-2">
            <div className="text-xs font-mono text-gray-600 italic">
              // Waiting for alert stream...
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;