import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import NouvelleRecherche from './pages/NouvelleRecherche';
import Historique from './pages/Historique';
import Configuration from './pages/Configuration';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/recherche" element={<NouvelleRecherche />} />
        <Route path="/historique" element={<Historique />} />
        <Route path="/configuration" element={<Configuration />} />
      </Routes>
    </Layout>
  );
}

export default App;
