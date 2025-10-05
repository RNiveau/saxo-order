import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';
import { Navigation } from './components/Navigation';
import { Home } from './components/Home';
import { AvailableFunds } from './components/AvailableFunds';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navigation />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/available-funds" element={<AvailableFunds />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
