
import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, Navigate } from 'react-router-dom';
import Menu from './Componentes/Menu';
import Asistencia from './Componentes/Asistencia';

import Reportes from './Componentes/Reportes';
import Horario from './Componentes/Ingresos/Horario';
import IngresoBaseDatos from './Componentes/Ingresos/IngresoBaseDatos';
import AsignacionServicio from './Componentes/Ingresos/AsignacionServicio';
import Modificacion from './Componentes/Ingresos/Modificacion';
import MainLayout from './Componentes/MainLayout';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [currentUser, setCurrentUser] = useState(null);


  /******************************************************************************************************** */
  const login = async () => {
      const res = await fetch('http://localhost:8000/api/login/', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    console.log(JSON.stringify({ username, password }));

    if (res.ok) {
      getUser();
      alert('Login correcto');
      console.log("exitoso");
    } else {
      alert('Login failed');
      console.log("fallado");
    }
  };

  /******************************************************************************************************** */

  const logout = async () => {
    await fetch('http://localhost:8000/api/logout/', {
      method: 'POST',
      credentials: 'include',
    });
    setCurrentUser(null);
  };

  /******************************************************************************************************** */

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

  /******************************************************************************************************** */

  const navigate = useNavigate();
  return (
    <div>
      {currentUser ? (
        <div>
        <Navigate to="/menu" replace />
        </div>
      ) : (
  <div className="login-container">
    <div className="login-box">
      <img src="logo.png" alt="Logo" className="logo" style={{ width: '250px', height: 'auto' }} />
      <form className="login-form">
        <label htmlFor="username">Nombre de usuario</label>
        <input type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />

        <label htmlFor="password">Contraseña</label>
        <div className="password-field">
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
          <i className="bi bi-eye-slash" id="togglePassword"></i>
        </div>

        <div className="options">
          <label><input type="checkbox" /> Recuérdame</label>
          <button type="button" className="btn" onClick={login}>Acceder</button>
        </div>
      </form>
      <a href="#" className="privacy-link">Privacidad</a>
    </div>
  </div>

      )}
    </div>
  );

  /*return (
   <button onClick={exportarExcel}>Exportar a Excel</button>
 );*/
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
       
        <Route path="/" element={<LoginPage />} />
        
        <Route path="/menu" element={<Menu />} />
         <Route element={<MainLayout />}>
        {/*<Route path="/asignacionServicio" element={<AsignacionServicio />} />*/}
        <Route path="/modificacion" element={<Modificacion />} />
        <Route path="/Horario" element={<Horario />} />
        <Route path="/creacionEntidades" element={<IngresoBaseDatos />} />
        <Route path="/asistencia" element={<Asistencia />} />
        <Route path="/reportes" element={<Reportes />} />
      </Route>
      </Routes>
    </BrowserRouter>
  );
}




export default App;


