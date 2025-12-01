import React, { useEffect, useState } from 'react';

function App() {
  const [message, setMessage] = useState('Loading...');

  useEffect(() => {
    const apiUrl = process.env.REACT_APP_API_URL || `http://${window.location.hostname}:8000`;

    fetch(`${apiUrl}/`)
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch(() => setMessage('Error connecting to API'));
  }, []);

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>FB Leads</h1>
      <p>API says: <strong>{message}</strong></p>
    </div>
  );
}

export default App;
