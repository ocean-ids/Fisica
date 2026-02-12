import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError, of } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const auth = inject(AuthService);
  const token = localStorage.getItem('access_token');
  
  // Agregar token si no expiró; si expiró, forzar logout inmediato
  if (token) {
    if (auth.isTokenExpired(token)) {
      auth.forceLogout();
      router.navigate(['/login']);
      return throwError(() => new Error('Token expirado'));
    }

    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }
  
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Si el error es 401 (no autorizado)
      if (error.status === 401) {
        // Si no es la página de login, hacer logout y redirigir
        if (!req.url.includes('/login/') && !req.url.includes('/token/refresh/')) {
          auth.forceLogout();
          router.navigate(['/login']);
        }
      }
      
      return throwError(() => error);
    })
  );
};
