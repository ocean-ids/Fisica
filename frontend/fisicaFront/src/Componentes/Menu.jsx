import React from 'react';
import { Link } from 'react-router-dom';
import './Menu.css';

function Menu() {
  return (
    <nav className="menu">
      <ul>
        <li className="dropdown">
          <span>Ingresos ▾</span>
          <ul className="dropdown-content">
            <li><Link to="/horario">Horario</Link></li>
            <li><Link to="/modificacion">Modificación Entidades</Link></li>
            <li><Link to="/creacionEntidades">Creación Entidades</Link></li>
            {/*<li><Link to="/asignacionServicio">Asignación Servicio</Link></li>*/}
            
          </ul>
        </li>
        <li><Link to="/horarios">Horarios</Link></li>
        <li><Link to="/asistencia">Asistencia</Link></li>
        <li><Link to="/reportes">Reportes</Link></li>
      </ul>
    </nav>
  );
}

export default Menu;