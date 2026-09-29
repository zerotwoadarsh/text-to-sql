// eslint-disable-next-line no-constant-binary-expression
const API_BASE_URL = "https://text-to-sql-wdia.onrender.com" || "http://localhost:8000";

export async function askQuestion(question) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`Server responded with status ${response.status}`);
  }

  return response.json();
}