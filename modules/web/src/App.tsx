import { useState } from "react";

import "./App.css";

function App() {
  const [count, setCount] = useState(0);
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";

  return (
    <main className="app">
      <h1>{title}</h1>
      <p>Web scaffold (PPT-047). Domain features land in later epic children.</p>
      <button type="button" onClick={() => setCount((value) => value + 1)}>
        Count is {count}
      </button>
    </main>
  );
}

export default App;
