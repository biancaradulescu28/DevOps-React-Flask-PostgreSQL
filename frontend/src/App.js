import React, { useState, useEffect } from 'react'; 
import logo from './logo.svg';
import './App.css';

function App() {
  const [data, setData] = useState('');

  useEffect(() => {
    fetch('/api/users')
      .then(response => response.text())
      .then(data => {
        console.log('Data fetched:', data);
        setData(data);
      })
      .catch(error => console.error('Error:', error));
  }, []);

  return (
    <div className="App">
      <h1>{data}</h1>
    </div>
  );
}

export default App;
