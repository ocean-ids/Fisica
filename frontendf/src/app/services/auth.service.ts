import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, BehaviorSubject, of, tap, catchError } from 'rxjs';
import type { LoginResponse } from '../models/login.models';
import { environment } from '@env/environment';
import Swal from 'sweetalert2';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.hasToken());
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();
  private tokenCheckId: any = null;

  // Cierre de sesión por inactividad (3 horas sin actividad del usuario)
  private readonly INACTIVITY_MS = 3 * 60 * 60 * 1000;
  private readonly WARNING_MS = 2 * 60 * 1000; // avisar 2 min antes
  private inactivityTimerId: any = null;
  private warningActive = false;
  private boundResetActivity = () => {
    this.lastActivityAt = Date.now();
    this.resetInactivityTimer();
  };

  // Renovación automática del token mientras el usuario esté activo.
  // El contador de "3 horas" es por INACTIVIDAD: si se usa la app, el token se
  // renueva y la sesión no se corta; si se deja quieta 3 h, se cierra.
  private lastActivityAt = Date.now();
  private readonly REFRESH_BEFORE_MS = 5 * 60 * 1000; // renovar 5 min antes de expirar
  private refreshing = false;


  constructor(private http: HttpClient, private router: Router) {
    this.startTokenWatcher();
    this.setupInactivityWatcher();
  }

  private setupInactivityWatcher(): void {
    const eventos = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    eventos.forEach(ev => window.addEventListener(ev, this.boundResetActivity, { passive: true }));
    if (this.hasToken()) {
      this.resetInactivityTimer();
    }
  }

  private resetInactivityTimer(): void {
    if (!this.hasToken()) return;
    // Mientras la alerta está visible, solo el botón "Seguir conectado" reinicia
    if (this.warningActive) return;
    if (this.inactivityTimerId) {
      clearTimeout(this.inactivityTimerId);
    }
    // Programar la ALERTA 2 min antes del cierre
    this.inactivityTimerId = setTimeout(() => {
      this.mostrarAvisoInactividad();
    }, this.INACTIVITY_MS - this.WARNING_MS);
  }

  private mostrarAvisoInactividad(): void {
    if (!this.hasToken()) return;
    this.warningActive = true;
    Swal.fire({
      icon: 'warning',
      title: 'Sesión por expirar',
      text: 'Tu sesión se cerrará por inactividad. ¿Deseas seguir conectado?',
      timer: this.WARNING_MS,
      timerProgressBar: true,
      showConfirmButton: true,
      confirmButtonText: 'Seguir conectado',
      allowOutsideClick: false,
    }).then(result => {
      this.warningActive = false;
      if (result.isConfirmed) {
        // El usuario sigue activo: reiniciar el contador
        this.resetInactivityTimer();
      } else {
        // No respondió a tiempo: cerrar sesión
        this.forceLogout();
        this.router.navigate(['/login']);
      }
    });
  }

  private withCacheBust(url?: string | null): string | null {
    if (!url) return null;
    const sep = url.includes('?') ? '&' : '?';
    return `${url}${sep}v=${Date.now()}`;
  }

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login/`, 
      { username, password }
    ).pipe(
      tap((response) => {
        // Guardar tokens en localStorage
        localStorage.setItem('access_token', response.access);
        localStorage.setItem('refresh_token', response.refresh);
        const user = {
          ...response.user,
          photo_url: this.withCacheBust(response.user?.photo_url ?? null)
        };
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('groups', JSON.stringify(response.user.groups ?? []));
        localStorage.setItem('permissions', JSON.stringify(response.user.permissions ?? []));
        this.isAuthenticatedSubject.next(true);
        this.resetInactivityTimer();
      })
    );
  }

  logout(): Observable<any> {
    const refreshToken = this.getRefreshToken();
    
    // Intentar hacer logout en el backend (blacklist). El cierre de sesión debe
    // ocurrir SIEMPRE, aunque el backend falle (token ya expirado/rotado/blacklist
    // o error de red): el blacklist es "mejor esfuerzo".
    if (refreshToken) {
      return this.http.post(`${this.apiUrl}/logout/`,
        { refresh: refreshToken }
      ).pipe(
        catchError(() => of({ message: 'Logout local' })),  // no bloquear el cierre por un 400/red
        tap(() => this.clearTokens())
      );
    } else {
      this.clearTokens();
      return of({ message: 'Logout exitoso' });
    }
  }

  /**
   * Limpia tokens y emite estado no autenticado sin llamar al backend.
   */
  forceLogout(): void {
    this.clearTokens();
  }

  private clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('groups');
    localStorage.removeItem('permissions');
    if (this.inactivityTimerId) {
      clearTimeout(this.inactivityTimerId);
      this.inactivityTimerId = null;
    }
    if (this.warningActive) {
      this.warningActive = false;
      Swal.close();
    }
    this.isAuthenticatedSubject.next(false);
  }

  private startTokenWatcher(): void {
    if (this.tokenCheckId) {
      clearInterval(this.tokenCheckId);
    }
    this.tokenCheckId = setInterval(() => {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      // ¿El usuario ha estado activo dentro de la ventana de inactividad?
      const activo = (Date.now() - this.lastActivityAt) < this.INACTIVITY_MS;

      if (this.isTokenExpired(token)) {
        // Token vencido: si sigue activo y hay refresh, intentar renovar
        // (p. ej. al volver de suspensión); si no, cerrar sesión.
        if (activo && this.getRefreshToken()) {
          this.tryRefresh();
        } else {
          this.forceLogout();
          this.router.navigate(['/login']);
        }
        return;
      }

      // Token aún válido pero por vencer y usuario activo → renovar antes de que expire.
      if (activo && this.expiresWithin(token, this.REFRESH_BEFORE_MS) && this.getRefreshToken()) {
        this.tryRefresh();
      }
    }, 30000); // chequeo cada 30s
  }

  /** ¿El token vence dentro de los próximos `ms` milisegundos? */
  private expiresWithin(token: string, ms: number): boolean {
    try {
      const [, payload] = token.split('.');
      const decoded = JSON.parse(atob(payload));
      const expMs = decoded?.exp ? decoded.exp * 1000 : 0;
      if (!expMs) return true;
      return (expMs - Date.now()) <= ms;
    } catch {
      return true;
    }
  }

  /** Renueva el access token con el refresh token; si falla, cierra sesión. */
  private tryRefresh(): void {
    if (this.refreshing || !this.getRefreshToken()) return;
    this.refreshing = true;
    this.refreshToken().subscribe({
      next: () => { this.refreshing = false; },
      error: () => {
        this.refreshing = false;
        this.forceLogout();
        this.router.navigate(['/login']);
      }
    });
  }

  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  refreshToken(): Observable<any> {
    return this.http.post(`${this.apiUrl}/token/refresh/`, {
      refresh: this.getRefreshToken()
    }).pipe(
      tap((response: any) => {
        localStorage.setItem('access_token', response.access);
        if (response.refresh) {
          localStorage.setItem('refresh_token', response.refresh);
        }
      })
    );
  }

  isLoggedIn(): boolean {
    return this.hasToken();
  }

  private hasToken(): boolean {
    const token = localStorage.getItem('access_token');
    if (!token) return false;
    if (this.isTokenExpired(token)) {
      this.clearTokens();
      return false;
    }
    return true;
  }

  isTokenExpired(token: string): boolean {
    try {
      const [, payload] = token.split('.');
      const decoded = JSON.parse(atob(payload));
      const expMs = decoded?.exp ? decoded.exp * 1000 : 0;
      if (!expMs) return true;
      return Date.now() >= expMs;
    } catch (e) {
      return true;
    }
  }

  getCurrentUser(): Observable<any> {
    return this.http.get(`${this.apiUrl}/user/`);
  }

  getUserFromStorage(): any {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  updateStoredUser(partial: any): void {
    const current = this.getUserFromStorage() || {};
    const merged = { ...current, ...partial };
    localStorage.setItem('user', JSON.stringify(merged));
  }

  updateProfilePhoto(file: File | null, remove: boolean = false): Observable<any> {
    const formData = new FormData();
    if (file) {
      formData.append('photo', file);
    }
    if (remove) {
      formData.append('remove', '1');
    }
    return this.http.put(`${this.apiUrl}/user/profile/`, formData).pipe(
      tap((profile: any) => {
        this.updateStoredUser({
          first_name: profile?.first_name,
          last_name: profile?.last_name,
          full_name: profile?.full_name,
          photo_url: this.withCacheBust(profile?.photo_url ?? null)
        });
      })
    );
  }

  hasPermission(permission: string): boolean {
    const user = this.getUserFromStorage();
    if (!user) return false;

    if (user.is_superuser === true) return true;

    const groups: string[] = JSON.parse(localStorage.getItem('groups') ?? '[]');
    if (groups.some(g => (g ?? '').toUpperCase() === 'ADMIN')) return true;

    const permissions: string[] = JSON.parse(localStorage.getItem('permissions') ?? '[]');
    return permissions.includes(permission);
  }

  getGroups(): string[] {
    return JSON.parse(localStorage.getItem('groups') ?? '[]');
  }

  // Módulos que el admin ocultó del menú para este usuario (no afecta datos).
  // Los superusuarios / ADMIN ven todo.
  isModuleHidden(moduleKey: string): boolean {
    if (!moduleKey) return false;
    const user = this.getUserFromStorage();
    if (!user) return false;
    if (user.is_superuser === true) return false;
    const groups: string[] = JSON.parse(localStorage.getItem('groups') ?? '[]');
    if (groups.some(g => (g ?? '').toUpperCase() === 'ADMIN')) return false;
    const ocultos: string[] = Array.isArray(user.modulos_ocultos) ? user.modulos_ocultos : [];
    return ocultos.includes(moduleKey);
  }

  solicitarResetPassword(email: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/solicitar-reset-password/`, { email });
  }

  resetPassword(uidb64: string, token: string, password: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/reset-password/${uidb64}/${token}/`, { password });
  }
}
