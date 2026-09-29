import { useState } from "react";
import { askQuestion } from "./api";

function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setErrorMsg(null);
    setResult(null);

    try {
      const data = await askQuestion(question);
      setResult(data);
    } catch (err) {
      setErrorMsg(`Failed to reach the server: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Text-to-SQL Analytics Agent</h1>
        <div className="flex flex-wrap gap-2 mb-4">
          {[
            "How many customers are there?",
            "What are the top 5 best-selling tracks?",
            "Which country has the most customers?",
          ].map((example) => (
            <button
              key={example}
              onClick={() => setQuestion(example)}
              className="text-xs px-3 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700
                 text-slate-300 border border-slate-700 transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2 mb-8">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about the database..."
            className="flex-1 px-4 py-2 rounded-lg bg-slate-800 border border-slate-700
                       focus:outline-none focus:border-blue-500 text-slate-100"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500
                       disabled:bg-slate-700 disabled:cursor-not-allowed
                       font-medium transition-colors"
          >
            {loading ? "Thinking..." : "Ask"}
          </button>
        </form>

        {errorMsg && (
          <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 mb-6">
            {errorMsg}
          </div>
        )}

        {result && !result.success && (
          <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 mb-6">
            <p className="font-medium mb-1">
              The agent couldn't answer this question.
            </p>
            <p className="text-sm text-slate-300">{result.error}</p>
            <p className="text-xs text-slate-400 mt-2">
              Retries attempted: {result.retry_count}
            </p>
          </div>
        )}

        {result && result.success && (
          <div className="space-y-6">
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-medium text-slate-400">
                  Generated SQL
                </h2>
                {result.retry_count > 0 && (
                  <span className="text-xs bg-amber-900/50 text-amber-300 px-2 py-1 rounded-full">
                    Self-corrected after {result.retry_count}{" "}
                    {result.retry_count === 1 ? "retry" : "retries"}
                  </span>
                )}
              </div>
              <pre className="text-sm bg-slate-950 p-3 rounded overflow-x-auto text-green-400">
                {result.sql}
              </pre>
            </div>

            {result.chart_base64 ? (
              <div className="bg-slate-800 rounded-lg p-4">
                <img
                  src={`data:image/png;base64,${result.chart_base64}`}
                  alt="Result chart"
                  className="w-full rounded"
                />
              </div>
            ) : (
              <div className="bg-slate-800/50 border border-dashed border-slate-700 rounded-lg p-4 text-sm text-slate-500 text-center">
                No chart available for this result
              </div>
            )}

            {result.data && result.data.length > 0 && (
              <div className="bg-slate-800 rounded-lg p-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      {Object.keys(result.data[0]).map((col) => (
                        <th
                          key={col}
                          className="text-left py-2 px-3 text-slate-400"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.data.map((row, i) => (
                      <tr key={i} className="border-b border-slate-800">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="py-2 px-3">
                            {String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;