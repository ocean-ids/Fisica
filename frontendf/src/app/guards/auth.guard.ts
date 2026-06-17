import { CanActivateFn, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

const dashboardRoutesByPermission = [
  { path: '/dashboard/clientes', permission: 'CoreFisica.view_cliente' },
  { path: '/dashboard/instalaciones', permission: 'CoreFisica.view_instalacion' },
  { path: '/dashboard/puestos', permission: 'CoreFisica.view_puesto' },
  { path: '/dashboard/personas', permission: 'CoreFisica.view_persona' },
  { path: '/dashboard/horarios', permission: 'CoreFisica.view_horario' },
  { path: '/dashboard/asignaciones', permission: 'CoreFisica.view_asignacion' },
  { path: '/dashboard/reporte-asistencia', permission: 'CoreFisica.view_reporteasistencia' },
  { path: '/dashboard/consolidado', permission: 'CoreFisica.view_consolidado' },
];

function getFirstAccessibleDashboardRoute(authService: AuthService): string | null {
  const accessibleRoute = dashboardRoutesByPermission.find(({ permission }) =>
    authService.hasPermission(permission)
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

  if (!authService.isLoggedIn()) {
    return router.createUrlTree(['/login']);
  }

  if (!permission || authService.hasPermission(permission)) {
    return true;
  }

  const firstAccessibleRoute = getFirstAccessibleDashboardRoute(authService);

  if (firstAccessibleRoute && firstAccessibleRoute !== state.url) {
    return router.createUrlTree([firstAccessibleRoute]);
  }

  return router.createUrlTree(['/dashboard']);
};
