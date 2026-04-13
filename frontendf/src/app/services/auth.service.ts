import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, BehaviorSubject, tap } from 'rxjs';
import type { LoginResponse } from '../models/login.models';
import { environment } from '@env/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.hasToken());
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();
  private tokenCheckId: any = null;


  
  constructor(private http: HttpClient, private router: Router) {
    this.startTokenWatcher();
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
      })
    );
  }

  logout(): Observable<any> {
    const refreshToken = this.getRefreshToken();
    
    // Intentar hacer logout en el backend (blacklist)
    if (refreshToken) {
      return this.http.post(`${this.apiUrl}/logout/`, 
        { refresh: refreshToken }
      ).pipe(
        tap(() => this.clearTokens())
      );
    } else {
      this.clearTokens();
      return new Observable(observer => {
        observer.next({ message: 'Logout exitoso' });
        observer.complete();
      });
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
    this.isAuthenticatedSubject.next(false);
  }

  private startTokenWatcher(): void {
    if (this.tokenCheckId) {
      clearInterval(this.tokenCheckId);
    }
    this.tokenCheckId = setInterval(() => {
      const token = localStorage.getItem('access_token');
      if (!token) return;
      if (this.isTokenExpired(token)) {
        this.forceLogout();
        this.router.navigate(['/login']);
      }
    }, 30000); // chequeo cada 30s
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

  solicitarResetPassword(email: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/solicitar-reset-password/`, { email });
  }

  resetPassword(uidb64: string, token: string, password: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/reset-password/${uidb64}/${token}/`, { password });
  }
}
