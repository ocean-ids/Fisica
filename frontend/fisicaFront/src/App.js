import React, { useState, useEffect } from 'react';

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [currentUser, setCurrentUser] = useState(null);

  const login = async () => {
    const res = await fetch('http://localhost:8000/api/login/', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (res.ok) {
      getUser();
    } else {
      alert('Login failed');
    }
  };

  const logout = async () => {
    await fetch('http://localhost:8000/api/logout/', {
      method: 'POST',
      credentials: 'include',
    });
    setCurrentUser(null);
  };

  const getUser = async () => {
    const res = await fetch('http://localhost:8000/api/user/', {
      method: 'GET',
      credentials: 'include',
    });

    if (res.ok) {
      const data = await res.json();
      setCurrentUser(data.username);
    }
  };

  useEffect(() => {
    getUser();
  }, []);

  return (
    <div>
      {currentUser ? (
        <div>
          <h1>Hola, {currentUser}</h1>
          <button onClick={logout}>Logout</button>
        </div>
      ) : (
        <div>
          <input placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
          <button onClick={login}>Login</button>
        </div>
      )}
    </div>
  );
}

export default App;