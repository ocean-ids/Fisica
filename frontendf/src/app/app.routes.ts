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
import { ConsolidadoComponent } from './pages/consolidado/consolidado.component';
import { ReporteGuardiaComponent } from './pages/reporte-guardia/reporte-guardia.component';
import { SacavacacionesComponent } from './pages/sacavacaciones/sacavacaciones.component';
import { ReportePagoComponent } from './pages/reporte-pago/reporte-pago.component';
import { TarifasPagoComponent } from './pages/tarifas-pago/tarifas-pago.component';

export const routes: Routes = [
  {path: '', component: LoginComponent},
  {path: 'login', redirectTo: '', pathMatch: 'full'},
  {path: 'forgot-password', component: ForgotPasswordComponent},
  {path: 'reset-password/:uidb64/:token', component: ResetPasswordComponent},
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'reporte-asistencia', pathMatch: 'full' },
      { path: 'clientes', component: ClientesComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_cliente', moduleKey: 'clientes' }},
      { path: 'instalaciones', component: InstalacionesComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_instalacion', moduleKey: 'instalaciones' }},
      { path: 'puestos', component: PuestosComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_puesto', moduleKey: 'puestos' }},
      { path: 'personas', component: PersonasComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_persona', moduleKey: 'personas' }},
      { path: 'horarios', component: HorariosComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_horario', moduleKey: 'horarios' }},
      { path: 'asignaciones', component: AsignacionesComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_asignacion', moduleKey: 'asignaciones' }},
      { path: 'reporte-asistencia', component: ReporteAsistenciaComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_reporteasistencia', moduleKey: 'reporte-asistencia' }},
      { path: 'consolidado', component: ConsolidadoComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_consolidado', moduleKey: 'consolidado' }},
      { path: 'reporte-guardia', component: ReporteGuardiaComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_reporteguardia', moduleKey: 'reporte-guardia' }},
      { path: 'sacavacaciones', component: SacavacacionesComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_asignacion', moduleKey: 'sacavacaciones' }},
      { path: 'reporte-pago', component: ReportePagoComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_reporteguardia', moduleKey: 'reporte-pago' }},
      { path: 'tarifas-pago', component: TarifasPagoComponent, canActivate: [permissionGuard], data: { permission: 'CoreFisica.view_reporteguardia', moduleKey: 'tarifas-pago' }},
    ]
  },
  { path: '**', redirectTo: ''}
];
