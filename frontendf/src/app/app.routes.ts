import { Routes } from '@angular/router';
import { DashboardComponent } from './layout/dashboard/dashboard.component';
import { ClientesComponent } from './pages/clientes/clientes.component';
import { PersonasComponent } from './pages/personas/personas.component';
import { InstalacionesComponent } from './pages/instalaciones/instalaciones.component';
import { LoginComponent } from './pages/login/login.component';
import { ForgotPasswordComponent } from './pages/login/forgot-password/forgot-password.component';
import { ResetPasswordComponent } from './pages/login/reset-password/reset-password.component';
import { authGuard } from './guards/auth.guard';
import { PuestosComponent } from './pages/puestos/puestos.component';
import { HorariosComponent } from './pages/horarios/horarios.component';
import { AsignacionesComponent } from './pages/asignaciones/asignaciones.component';
import { AsignacionCalendarioComponent } from './pages/asignacion-calendario/asignacion-calendario.component';
import { PatronesListComponent } from './pages/patrones/patrones-list/patrones-list.component';

export const routes: Routes = [
  {path: '', component: LoginComponent},
  {path: '', component: LoginComponent},
  {path: 'forgot-password', component: ForgotPasswordComponent},
  {path: 'reset-password/:uidb64/:token', component: ResetPasswordComponent},
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
      { path: 'horarios', component: HorariosComponent},
      { path: 'asignaciones', component: AsignacionesComponent},
      { path: 'patrones', component: PatronesListComponent}
    ]
  },
  { path: '**', redirectTo: ''}
];
