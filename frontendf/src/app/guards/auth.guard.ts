import { CanActivateFn, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

// Todos los módulos del dashboard (mismo orden que el menú). Debe estar COMPLETA
// para poder aterrizar al usuario en su primer módulo accesible tras el login.
const dashboardRoutesByPermission = [
  { path: '/dashboard/clientes', permission: 'CoreFisica.view_cliente', key: 'clientes' },
  { path: '/dashboard/instalaciones', permission: 'CoreFisica.view_instalacion', key: 'instalaciones' },
  { path: '/dashboard/puestos', permission: 'CoreFisica.view_puesto', key: 'puestos' },
  { path: '/dashboard/personas', permission: 'CoreFisica.view_persona', key: 'personas' },
  { path: '/dashboard/horarios', permission: 'CoreFisica.view_horario', key: 'horarios' },
  { path: '/dashboard/asignaciones', permission: 'CoreFisica.view_asignacion', key: 'asignaciones' },
  { path: '/dashboard/reporte-asistencia', permission: 'CoreFisica.view_reporteasistencia', key: 'reporte-asistencia' },
  { path: '/dashboard/consolidado', permission: 'CoreFisica.view_consolidado', key: 'consolidado' },
  { path: '/dashboard/reporte-guardia', permission: 'CoreFisica.view_reporteguardia', key: 'reporte-guardia' },
  { path: '/dashboard/sacavacaciones', permission: 'CoreFisica.view_asignacion', key: 'sacavacaciones' },
];

function getFirstAccessibleDashboardRoute(authService: AuthService): string | null {
  // El primer módulo con permiso Y que no esté oculto para este usuario.
  const accessibleRoute = dashboardRoutesByPermission.find(({ permission, key }) =>
    authService.hasPermission(permission) && !authService.isModuleHidden(key)
  );

  return accessibleRoute?.path ?? null;
}

export const authGuard: CanActivateFn = (_route, state: RouterStateSnapshot) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isLoggedIn()) {
    return router.createUrlTree(['/login']);
  }

  if (state.url === '/dashboard' || state.url === '/dashboard/') {
    const firstAccessibleRoute = getFirstAccessibleDashboardRoute(authService);
    if (firstAccessibleRoute) {
      return router.createUrlTree([firstAccessibleRoute]);
    }
    // Sin ningún módulo accesible/visible: cerrar sesión para no quedar en bucle.
    authService.forceLogout();
    return router.createUrlTree(['/login']);
  }

  return true;
};

export const permissionGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const permission: string = route.data['permission'];
  const moduleKey: string = route.data['moduleKey'];

  if (!authService.isLoggedIn()) {
    return router.createUrlTree(['/login']);
  }

  // Módulo oculto por el admin: no accesible ni por URL (aunque tenga el dato).
  const oculto = moduleKey && authService.isModuleHidden(moduleKey);

  if (!oculto && (!permission || authService.hasPermission(permission))) {
    return true;
  }

  const firstAccessibleRoute = getFirstAccessibleDashboardRoute(authService);

  if (firstAccessibleRoute && firstAccessibleRoute !== state.url) {
    return router.createUrlTree([firstAccessibleRoute]);
  }

  // No hay a dónde mandarlo: cerrar sesión para evitar el bucle de redirección.
  authService.forceLogout();
  return router.createUrlTree(['/login']);
};
