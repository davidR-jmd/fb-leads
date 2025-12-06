import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import Dashboard from './pages/Dashboard';
import NouvelleRecherche from './pages/NouvelleRecherche';
import Historique from './pages/Historique';
import Configuration from './pages/Configuration';
import AdminUsers from './pages/AdminUsers';
import LinkedInSettings from './pages/LinkedInSettings';
import LinkedInSearch from './pages/LinkedInSearch';
import Login from './pages/Login';
import Register from './pages/Register';

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected routes */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/recherche" element={<NouvelleRecherche />} />
                <Route path="/historique" element={<Historique />} />
                <Route path="/configuration" element={<Configuration />} />
                <Route path="/linkedin/search" element={<LinkedInSearch />} />
                <Route
                  path="/admin/users"
                  element={
                    <AdminRoute>
                      <AdminUsers />
                    </AdminRoute>
                  }
                />
                <Route
                  path="/admin/linkedin"
                  element={
                    <AdminRoute>
                      <LinkedInSettings />
                    </AdminRoute>
                  }
                />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
