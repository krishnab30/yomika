import "./App.css";

import Header from "./components/Header";
import UploadBook from "./components/UploadBook";

function App() {
  return (
    <main>
      <Header />

      <p>
        Turn your light novels into audiobooks.
      </p>

      <UploadBook />
    </main>
  );
}

export default App;