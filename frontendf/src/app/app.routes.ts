import { Routes } from '@angular/router';
import { DashboardComponent } from './layout/dashboard/dashboard.component';
import { ClientesComponent } from './pages/clientes/clientes.component';
import { PersonasComponent } from './pages/personas/personas.component';
import { InstalacionesComponent } from './pages/instalaciones/instalaciones.component';
import { LoginComponent } from './pages/login/login.component';
import { authGuard } from './guards/auth.guard';
import { PuestosComponent } from './pages/puestos/puestos.component';
import { HorariosComponent } from './pages/horarios/horarios.component';

export const routes: Routes = [
  {path: '', component: LoginComponent},
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'clientes', pathMatch: 'full' },
      { path: 'clientes', component: ClientesComponent},
      { path: 'instalaciones', component: InstalacionesComponent},
      { path: 'puestos', component: PuestosComponent},
      { path: 'personas', component: PersonasComponent},
      { path: 'horarios', component: HorariosComponent}
    ]
  },
  { path: '**', redirectTo: ''}
];
