import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const token = localStorage.getItem('access_token');
  
  // Agregar token a la petición si existe
  if (token) {
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
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          router.navigate(['/login']);
        }
      }
      
      return throwError(() => error);
    })
  );
};
