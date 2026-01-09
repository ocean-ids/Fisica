import React from 'react';
import Menu from './Menu';
import { Outlet } from 'react-router-dom';

const MainLayout = () => (
  <>
    <Menu />
    <div className="contenido">
      <Outlet />
    </div>
  </>
);

export default MainLayout;