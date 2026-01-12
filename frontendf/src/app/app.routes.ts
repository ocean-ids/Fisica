import { Routes } from '@angular/router';
import { DashboardComponent } from './layout/dashboard/dashboard.component';
import { ClientesComponent } from './pages/clientes/clientes.component';
import { PersonasComponent } from './pages/personas/personas.component';
import { InstalacionesComponent } from './pages/instalaciones/instalaciones.component';
import { PuestosComponent } from './pages/puestos/puestos.component';
import { HorariosComponent } from './pages/horarios/horarios.component';
import { AsignacionesComponent } from './pages/asignaciones/asignaciones.component';
import { ReportesComponent } from './pages/reportes/reportes.component';

export const routes: Routes = [
  {
    path: '',
    component: DashboardComponent,
    children: [
      { path: '', redirectTo: 'clientes', pathMatch: 'full' },
      { path: 'clientes', component: ClientesComponent}
    ]
  }
];
