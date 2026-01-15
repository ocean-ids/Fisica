import { Routes } from '@angular/router';
import { DashboardComponent } from './layout/dashboard/dashboard.component';
import { ClientesComponent } from './pages/clientes/clientes.component';
import { PersonasComponent } from './pages/personas/personas.component';
import { InstalacionesComponent } from './pages/instalaciones/instalaciones.component';
import { AsignacionesComponent } from './pages/asignaciones/asignaciones.component';
import { LoginComponent } from './pages/login/login.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {path: 'login', component: LoginComponent},
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'clientes', pathMatch: 'full' },
      { path: 'clientes', component: ClientesComponent},
      { path: 'personas', component: PersonasComponent},
      { path: 'instalaciones', component: InstalacionesComponent},
    ]
  },
  { path: '**', redirectTo: 'login'}
];
