import { Routes } from '@angular/router';
import { DashboardComponent } from './layout/dashboard/dashboard.component';
import { ClientesComponent } from './pages/clientes/clientes.component';
import { PersonasComponent } from './pages/personas/personas.component';
import { InstalacionesComponent } from './pages/instalaciones/instalaciones.component';
import { LoginComponent } from './pages/login/login.component';
import { ForgotPasswordComponent } from './pages/login/forgot-password/forgot-password.component';
import { ResetPasswordComponent } from './pages/login/reset-password/reset-password.component';
import { authGuard, permissionGuard } from './guards/auth.guard';
import { PuestosComponent } from './pages/puestos/puestos.component';
import { HorariosComponent } from './pages/horarios/horarios.component';
import { AsignacionesComponent } from './pages/asignaciones/asignaciones.component';
import { AsignacionCalendarioComponent } from './pages/asignacion-calendario/asignacion-calendario.component';
import { ReporteAsistenciaComponent } from './pages/reporte-asistencia/reporte-asistencia.component';
import { PersonalConsolaComponent } from './pages/personal-consola/personal-consola.component';


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
      { path: '', redirectTo: 'reporte-asistencia', pathMatch: 'full' },
      { path: 'clientes', component: ClientesComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_cliente' }},
      { path: 'instalaciones', component: InstalacionesComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_instalacion' }},
      { path: 'puestos', component: PuestosComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_puesto' }},
      { path: 'personas', component: PersonasComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_persona' }},
      { path: 'horarios', component: HorariosComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_horario' }},
      { path: 'asignaciones', component: AsignacionesComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_asignacion' }},
      { path: 'reporte-asistencia', component: ReporteAsistenciaComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_reporteasistencia' }},
      { path: 'personal-consola', component: PersonalConsolaComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_personalconsola' }}
    ]
  },
  { path: '**', redirectTo: ''}
];
